import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    Product,
    ProductBrainVersion,
    XiaohongshuContent,
    XiaohongshuOpportunity,
    now,
)
from .xiaohongshu_client import XiaohongshuError
from .prompting import draft_prompt

logger = logging.getLogger(__name__)


class XiaohongshuTargetError(RuntimeError):
    pass


def validate_xiaohongshu_draft(body: str, *, allowed_disclosure: str = "") -> str:
    normalized = body.strip()
    if normalized.upper() == "SKIP":
        raise ValueError("当前内容不适合自动回复")
    false_affiliation = "我是" in normalized and any(
        word in normalized for word in ("开发者", "官方", "团队成员", "工作人员")
    )
    if false_affiliation and (not allowed_disclosure or allowed_disclosure not in normalized):
        raise ValueError("草稿包含未经验证的身份声明")
    if "http://" in normalized or "https://" in normalized:
        raise ValueError("草稿不能包含链接")
    if len(normalized) < 6:
        raise ValueError("草稿内容过短")
    if len(normalized) > 25:
        raise ValueError("草稿超过 25 个字符")
    return normalized


def ensure_daily_quota(comments_today: int, daily_limit: int) -> None:
    if comments_today >= daily_limit:
        raise RuntimeError("今天已达到该产品的评论上限")


def _comment_exists(comments: list[dict[str, Any]], comment_id: str) -> bool:
    for comment in comments:
        if str(comment.get("id") or "") == comment_id:
            return True
        if _comment_exists(comment.get("subComments") or [], comment_id):
            return True
    return False


# ---------------------------------------------------------------------------
# Issue #1 — Auto-generate search keywords from Product Brain
# ---------------------------------------------------------------------------


async def auto_search_keywords(
    db: AsyncSession, product_id: str, provider=None, *, limit: int = 3
) -> list[str]:
    """Select a small, Chinese, pain-led keyword set for the current run."""
    brain = await db.scalar(
        select(ProductBrainVersion).where(
            ProductBrainVersion.product_id == product_id,
            ProductBrainVersion.is_current,
        )
    )
    if brain is None:
        return []

    brain_data = brain.brain_json
    graph = brain_data.get("query_graph", {})

    if provider is not None:
        schema = {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": limit,
                    "items": {
                        "type": "object",
                        "properties": {
                            "keyword": {"type": "string"},
                            "selection_reason": {"type": "string"},
                        },
                        "required": ["keyword", "selection_reason"],
                    },
                }
            },
            "required": ["keywords"],
        }
        payload = {
            "product_name": brain_data.get("product_name", ""),
            "target_users": brain_data.get("target_users", []),
            "pain_points": brain_data.get("pain_points", []),
            "jobs_to_be_done": brain_data.get("jobs_to_be_done", []),
            "use_cases": brain_data.get("use_cases", []),
            "query_graph": graph,
            "count": limit,
        }
        try:
            result = await provider.generate_structured(
                "select_search_keywords", payload, schema
            )
            selected = [
                str(item.get("keyword", "")).strip()
                for item in result.get("keywords", [])
                if isinstance(item, dict)
            ]
            selected = [term for term in selected if _valid_xhs_keyword(term)]
            if selected:
                return list(dict.fromkeys(selected))[:limit]
        except Exception as error:
            logger.warning("LLM keyword selection failed, using Brain terms: %s", error)

    pool: list[str] = []
    for source in ("pain_phrases", "use_cases", "direct_terms", "intent_patterns"):
        for term in graph.get(source, []):
            cleaned = str(term).strip()
            if _valid_xhs_keyword(cleaned) and cleaned not in pool:
                pool.append(cleaned)
    return pool[:limit]


def _valid_xhs_keyword(term: str) -> bool:
    return bool(2 <= len(term) <= 16 and re.search(r"[\u4e00-\u9fff]", term))


# ---------------------------------------------------------------------------
# Issue #3 — Smarter target refresh (try stored token first, fallback search)
# ---------------------------------------------------------------------------


async def refresh_xiaohongshu_target(client, content) -> str:
    """Refresh the xsec_token for the target note/comment before publishing.

    Strategy:
    1. First try the stored xsec_token directly via feed_detail — avoids re-search.
    2. If that fails, fall back to searching by the original keyword and matching.
    """
    feed_id = content.parent_content_id or content.platform_content_id
    stored_token = content.xsec_token or ""

    # Step 1: Try stored token
    if stored_token:
        try:
            detail = await client.feed_detail(feed_id, stored_token)
            detail_data = detail.get("data") or detail
            if content.target_type == "COMMENT":
                comments = (detail_data.get("comments") or {}).get("list") or []
                if not _comment_exists(comments, content.platform_content_id):
                    raise XiaohongshuTargetError("目标评论已不存在，请重新选择机会")
            return stored_token
        except XiaohongshuError:
            logger.info(
                "Stored xsec_token expired for feed %s, attempting search refresh", feed_id
            )

    # Step 2: Fall back to search
    try:
        search = await client.search_feeds(content.source_keyword)
    except XiaohongshuError as error:
        raise XiaohongshuTargetError(
            f"无法通过搜索刷新目标令牌：{error}"
        ) from error

    matches = normalize_search_results(search, keyword=content.source_keyword)
    match = next(
        (row for row in matches if row["platform_content_id"] == feed_id),
        None,
    )
    if match is None:
        raise XiaohongshuTargetError(
            "目标笔记在当前搜索结果中未找到。可能已被删除或搜索排名变化，请重新搜索机会。"
        )

    fresh_token = match["xsec_token"]
    detail = await client.feed_detail(feed_id, fresh_token)
    detail_data = detail.get("data") or detail
    if content.target_type == "COMMENT":
        comments = (detail_data.get("comments") or {}).get("list") or []
        if not _comment_exists(comments, content.platform_content_id):
            raise XiaohongshuTargetError("目标评论已不存在，请重新选择机会")
    content.xsec_token = fresh_token
    return fresh_token


async def execute_xiaohongshu_action(
    client, content, body: str, *, fresh_token: str | None = None
):
    fresh_token = fresh_token or await refresh_xiaohongshu_target(client, content)
    if content.target_type == "COMMENT":
        return await client.reply(
            content.parent_content_id,
            fresh_token,
            body,
            comment_id=content.platform_content_id,
            user_id=getattr(content, "author_id", "") or "",
        )
    return await client.comment(content.platform_content_id, fresh_token, body)


def _user(data: dict[str, Any], key: str = "user") -> tuple[str, str]:
    user = data.get(key) or {}
    return (
        str(user.get("userId") or user.get("user_id") or ""),
        str(user.get("nickname") or user.get("nickName") or ""),
    )


# ---------------------------------------------------------------------------
# Issue #2 — Robust search result normalization (filter invalid entries)
# ---------------------------------------------------------------------------


def normalize_search_results(payload: dict[str, Any], *, keyword: str) -> list[dict[str, Any]]:
    """Normalize the MCP search response while retaining the token required for detail calls."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for feed in payload.get("feeds") or []:
        if feed.get("modelType") not in (None, "note"):
            continue
        feed_id = str(feed.get("id") or "")
        if not feed_id or feed_id in seen:
            continue
        xsec_token = str(feed.get("xsecToken") or feed.get("xsec_token") or "")
        # Skip entries without a valid token — they can't be used for detail/comment
        if not xsec_token:
            logger.debug("Skipping feed %s without xsec_token", feed_id)
            continue
        seen.add(feed_id)
        card = feed.get("noteCard") or feed.get("note_card") or {}
        author_id, author_name = _user(card)
        rows.append(
            {
                "platform": "xiaohongshu",
                "platform_content_id": feed_id,
                "xsec_token": xsec_token,
                "title": str(card.get("displayTitle") or card.get("display_title") or ""),
                "author_id": author_id,
                "author_name": author_name,
                "source_keyword": keyword,
                "raw_json": feed,
            }
        )
    return rows


def opportunity_records(
    detail: dict[str, Any], *, source_keyword: str
) -> list[dict[str, Any]]:
    """Create stable note and first-level comment targets from a feed detail response."""
    detail = detail.get("data") or detail
    note = detail.get("note") or {}
    note_id = str(note.get("noteId") or note.get("note_id") or "")
    xsec_token = str(note.get("xsecToken") or note.get("xsec_token") or "")
    author_id, author_name = _user(note)
    rows = [
        {
            "platform": "xiaohongshu",
            "target_type": "NOTE",
            "platform_content_id": note_id,
            "parent_content_id": None,
            "xsec_token": xsec_token,
            "title": str(note.get("title") or ""),
            "body": str(note.get("desc") or ""),
            "author_id": author_id,
            "author_name": author_name,
            "source_keyword": source_keyword,
            "dedupe_key": f"xiaohongshu:NOTE:{note_id}",
            "raw_json": note,
        }
    ]
    comments = (detail.get("comments") or {}).get("list") or []
    for comment in comments:
        comment_id = str(comment.get("id") or "")
        if not comment_id:
            continue
        comment_author_id, comment_author_name = _user(comment, "userInfo")
        rows.append(
            {
                "platform": "xiaohongshu",
                "target_type": "COMMENT",
                "platform_content_id": comment_id,
                "parent_content_id": note_id,
                "xsec_token": xsec_token,
                "title": str(note.get("title") or ""),
                "body": str(comment.get("content") or ""),
                "author_id": comment_author_id,
                "author_name": comment_author_name,
                "source_keyword": source_keyword,
                "dedupe_key": f"xiaohongshu:COMMENT:{note_id}:{comment_id}",
                "raw_json": comment,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Issue #2 — Fault-tolerant import (individual feed failures don't block all)
# ---------------------------------------------------------------------------


async def evaluate_xiaohongshu_opportunity(
    db: AsyncSession,
    product_id: str,
    title: str,
    body: str,
    target_type: str,
    provider,
) -> dict[str, Any]:
    product = await db.get(Product, product_id)
    brain = await db.scalar(
        select(ProductBrainVersion).where(
            ProductBrainVersion.product_id == product_id,
            ProductBrainVersion.is_current,
        )
    )
    brain_data = brain.brain_json if brain else {}

    payload = {
        "product_name": product.name if product else "",
        "target_users": brain_data.get("target_users", []),
        "pain_points": brain_data.get("pain_points", []),
        "use_cases": brain_data.get("use_cases", []),
        "recommend_when": brain_data.get("recommend_when", []),
        "do_not_recommend_when": brain_data.get("do_not_recommend_when", []),
        "verified_capabilities": [
            item.get("claim", "")
            for item in brain_data.get("supported_claims", [])[:5]
        ],
        "content_title": title,
        "content_body": body,
        "target_type": target_type,
    }

    schema = {
        "type": "object",
        "properties": {
            "opportunity_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "risk_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "reasoning": {"type": "string"},
            "match_signals": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["opportunity_score", "risk_score", "reasoning", "match_signals"],
    }

    try:
        res = await provider.generate_structured("evaluate_opportunity", payload, schema)
        opportunity_score = float(res.get("opportunity_score", 0.5))
        risk_score = float(res.get("risk_score", 0.2))
        if 1 < opportunity_score <= 100:
            opportunity_score /= 100
        if 1 < risk_score <= 100:
            risk_score /= 100
        return {
            "opportunity_score": min(1.0, max(0.0, opportunity_score)),
            "risk_score": min(1.0, max(0.0, risk_score)),
            "score_reason": str(res.get("reasoning", ""))[:1000],
            "match_signals": [str(item)[:120] for item in res.get("match_signals", [])[:8]],
        }
    except Exception as e:
        logger.warning("LLM opportunity scoring failed: %s. Falling back to heuristic.", e)
        text = f"{title} {body}"
        demand_signal = any(mark in text for mark in ("?", "？", "求", "推荐", "有没有", "怎么"))
        # A model outage must never turn a loose keyword match into an automatic
        # external comment. Heuristic rows stay below the 75-point publish gate.
        return {
            "opportunity_score": 0.64 if demand_signal else 0.35,
            "risk_score": 0.3,
            "score_reason": "模型评分不可用，已降级为保守候选，不会自动发布",
            "match_signals": ["包含求助表达"] if demand_signal else [],
        }


async def import_search_opportunities(
    db: AsyncSession, product_id: str, client, keyword: str, provider, *, detail_limit: int = 5
) -> list[XiaohongshuOpportunity]:
    search_payload = await client.search_feeds(keyword)
    search_rows = normalize_search_results(search_payload, keyword=keyword)
    imported: list[XiaohongshuOpportunity] = []
    errors: list[str] = []

    for search_row in search_rows[:detail_limit]:
        try:
            detail = await client.feed_detail(
                search_row["platform_content_id"], search_row["xsec_token"]
            )
        except XiaohongshuError as error:
            logger.warning(
                "Skipping feed %s: %s", search_row["platform_content_id"], error
            )
            errors.append(f"笔记 {search_row['platform_content_id'][:8]}… 获取失败")
            if "超时" in str(error) or "无法连接" in str(error):
                raise
            continue

        for record in opportunity_records(detail, source_keyword=keyword):
            content = await db.scalar(
                select(XiaohongshuContent).where(
                    XiaohongshuContent.dedupe_key == record["dedupe_key"]
                )
            )
            if content is None:
                content = XiaohongshuContent(
                    dedupe_key=record["dedupe_key"],
                    target_type=record["target_type"],
                    platform_content_id=record["platform_content_id"],
                    parent_content_id=record["parent_content_id"],
                    xsec_token=record["xsec_token"],
                    title=record["title"],
                    body=record["body"],
                    author_id=record["author_id"],
                    author_name=record["author_name"],
                    source_keyword=record["source_keyword"],
                    raw_json=record["raw_json"],
                )
                db.add(content)
                await db.flush()
            opportunity = await db.scalar(
                select(XiaohongshuOpportunity).where(
                    XiaohongshuOpportunity.product_id == product_id,
                    XiaohongshuOpportunity.content_id == content.id,
                )
            )
            if opportunity is None:
                evaluation = await evaluate_xiaohongshu_opportunity(
                    db, product_id, content.title, content.body, content.target_type, provider
                )
                opportunity = XiaohongshuOpportunity(
                    product_id=product_id,
                    content_id=content.id,
                    opportunity_score=evaluation["opportunity_score"],
                    risk_score=evaluation["risk_score"],
                    score_reason=evaluation["score_reason"],
                    match_signals=evaluation["match_signals"],
                    evaluated_at=now(),
                )
                db.add(opportunity)
            imported.append(opportunity)
    await db.commit()

    if not imported and errors:
        logger.error("All feed details failed for keyword '%s': %s", keyword, errors)

    return imported


async def generate_xiaohongshu_draft(db: AsyncSession, opportunity, provider) -> str:
    await db.refresh(opportunity, ["content"])
    product = await db.get(Product, opportunity.product_id)
    brain = await db.scalar(
        select(ProductBrainVersion).where(
            ProductBrainVersion.product_id == opportunity.product_id,
            ProductBrainVersion.is_current,
        )
    )
    brain_data = brain.brain_json if brain else {}
    disclosure = (product.disclosure_template or "").strip() if product else ""
    may_promote = bool(
        product
        and product.is_owned
        and disclosure
        and brain_data.get("supported_claims")
    )
    prompt = draft_prompt(
        product={
            "name": product.name if product else "",
            "is_owned": product.is_owned if product else False,
            "disclosure_template": disclosure,
        },
        brain=brain_data,
        opportunity={
            "target_type": opportunity.content.target_type,
            "title": opportunity.content.title,
            "body": opportunity.content.body,
            "author_name": opportunity.content.author_name,
        },
    )
    last_error: ValueError | None = None
    for attempt in range(2):
        retry_note = (
            "\n上次输出不合格。只输出 6-25 个字符的一句话；不合适则输出 SKIP。"
            if attempt
            else ""
        )
        body = (await provider.generate_text(prompt + retry_note)).strip()[:500]
        if not body:
            last_error = ValueError("模型没有生成评论草稿")
            continue
        try:
            validated = validate_xiaohongshu_draft(
                body, allowed_disclosure=disclosure if may_promote else ""
            )
            if not may_promote and product and product.name.lower() in validated.lower():
                raise ValueError("缺少真实关系披露，不能自动推广产品")
            return validated
        except ValueError as error:
            last_error = error
    raise last_error or ValueError("模型没有生成合格评论草稿")


async def generate_qualifying_drafts(
    db: AsyncSession,
    opportunity_ids: list[str],
    provider,
    *,
    threshold: float = 0.75,
    risk_threshold: float = 0.35,
) -> int:
    generated = 0
    for opportunity_id in opportunity_ids:
        opportunity = await db.scalar(
            select(XiaohongshuOpportunity)
            .options(selectinload(XiaohongshuOpportunity.content))
            .where(XiaohongshuOpportunity.id == opportunity_id)
        )
        if (
            opportunity is None
            or opportunity.opportunity_score < threshold
            or opportunity.risk_score > risk_threshold
        ):
            continue
        # Rebuild even an existing READY draft when the content is seen in a new
        # cycle. Prompt and safety rules evolve; a legacy draft must never be
        # treated as trusted merely because it was generated once.
        try:
            opportunity.draft_body = await generate_xiaohongshu_draft(db, opportunity, provider)
            opportunity.draft_status = "READY"
            opportunity.draft_generated_at = now()
            generated += 1
        except (ValueError, RuntimeError) as error:
            logger.warning("Draft generation failed for opportunity %s: %s", opportunity_id, error)
            continue
    await db.commit()
    return generated


def _aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


async def publish_best_qualifying_opportunity(
    db: AsyncSession,
    product: Product,
    client,
    *,
    kill_switch: bool = False,
    opportunity_ids: list[str] | None = None,
) -> XiaohongshuOpportunity | None:
    """Publish at most one freshly evaluated draft, guarded by cooldown and quota."""
    if kill_switch or not product.autopublish_enabled:
        return None

    current = now()
    last_publish = _aware(product.last_auto_publish_at)
    if last_publish and current - last_publish < timedelta(
        hours=product.min_publish_interval_hours
    ):
        return None

    day_start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    comments_today = await db.scalar(
        select(func.count(XiaohongshuOpportunity.id)).where(
            XiaohongshuOpportunity.product_id == product.id,
            XiaohongshuOpportunity.commented_at >= day_start,
        )
    )
    if (comments_today or 0) >= product.daily_reply_limit:
        return None

    query = (
        select(XiaohongshuOpportunity)
        .options(selectinload(XiaohongshuOpportunity.content))
        .where(
            XiaohongshuOpportunity.product_id == product.id,
            XiaohongshuOpportunity.status == "DISCOVERED",
            XiaohongshuOpportunity.opportunity_score >= product.auto_score_threshold,
            XiaohongshuOpportunity.risk_score <= product.auto_risk_threshold,
            XiaohongshuOpportunity.draft_status == "READY",
            XiaohongshuOpportunity.draft_body.is_not(None),
        )
        .order_by(
            XiaohongshuOpportunity.opportunity_score.desc(),
            XiaohongshuOpportunity.created_at,
        )
        .with_for_update(skip_locked=True)
    )
    # Automation may only publish from candidates evaluated in this exact search
    # cycle. This prevents old, lower-quality drafts produced by an earlier prompt
    # version from leaking into the unattended publish queue.
    if opportunity_ids is not None:
        if not opportunity_ids:
            return None
        query = query.where(XiaohongshuOpportunity.id.in_(opportunity_ids))

    opportunity = await db.scalar(query)
    if opportunity is None:
        return None

    try:
        opportunity.draft_body = validate_xiaohongshu_draft(
            opportunity.draft_body or "",
            allowed_disclosure=(product.disclosure_template or "").strip(),
        )
    except ValueError as error:
        opportunity.draft_status = "REJECTED"
        opportunity.publish_error = f"草稿安全检查未通过：{error}"
        await db.commit()
        return None

    status = await client.login_status()
    if not status.get("is_logged_in"):
        raise XiaohongshuError("小红书登录状态已失效，请重新扫码登录")

    try:
        fresh_token = await refresh_xiaohongshu_target(client, opportunity.content)
        await execute_xiaohongshu_action(
            client,
            opportunity.content,
            opportunity.draft_body,
            fresh_token=fresh_token,
        )
    except (XiaohongshuError, XiaohongshuTargetError) as error:
        # Do not retry an external write after an ambiguous response. This avoids
        # duplicate comments when the platform accepted a request but lost the reply.
        opportunity.status = "PUBLISH_UNKNOWN"
        opportunity.publish_error = str(error)[:2000]
        await db.commit()
        raise

    opportunity.status = "COMMENTED"
    opportunity.commented_at = current
    opportunity.publish_error = None
    product.last_auto_publish_at = current
    await db.commit()
    return opportunity


async def manually_generate_and_publish_opportunity(
    db: AsyncSession, opportunity_id: str, provider, client
) -> XiaohongshuOpportunity:
    """Generate and publish one user-selected opportunity regardless of its score."""
    opportunity = await db.scalar(
        select(XiaohongshuOpportunity)
        .options(selectinload(XiaohongshuOpportunity.content))
        .where(XiaohongshuOpportunity.id == opportunity_id)
    )
    if opportunity is None:
        raise ValueError("发现结果不存在")
    if opportunity.status == "COMMENTED":
        raise ValueError("这条内容已经发布过回复")
    if opportunity.status == "PUBLISH_UNKNOWN":
        raise ValueError("上次发布状态待确认，为避免重复评论不能再次发送")

    opportunity.draft_body = await generate_xiaohongshu_draft(db, opportunity, provider)
    opportunity.draft_status = "READY"
    opportunity.draft_generated_at = now()
    opportunity.publish_error = None
    await db.commit()

    login = await client.login_status()
    if not login.get("is_logged_in"):
        raise XiaohongshuError("小红书登录状态已失效，请重新扫码登录")

    try:
        fresh_token = await refresh_xiaohongshu_target(client, opportunity.content)
        await execute_xiaohongshu_action(
            client,
            opportunity.content,
            opportunity.draft_body,
            fresh_token=fresh_token,
        )
    except (XiaohongshuError, XiaohongshuTargetError) as error:
        opportunity.status = "PUBLISH_UNKNOWN"
        opportunity.publish_error = str(error)[:2000]
        await db.commit()
        raise

    current = now()
    opportunity.status = "COMMENTED"
    opportunity.commented_at = current
    opportunity.publish_error = None
    product = await db.get(Product, opportunity.product_id)
    if product:
        product.last_auto_publish_at = current
    await db.commit()
    await db.refresh(opportunity, ["content"])
    return opportunity
