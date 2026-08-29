import base64
import hashlib
import hmac
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from redis.asyncio import Redis
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .automation import AutomationError, run_product_automation
from .config import get_settings
from .database import get_db
from .ingestion import ingest_url
from .managed_llm import forward_managed_chat, managed_gateway_ready
from .models import (
    Candidate,
    Conversation,
    GeneratedReply,
    PolicyDecision,
    Product,
    ProductBrainVersion,
    ProductSource,
    ProductSubreddit,
    PublishedReply,
    RedditAccount,
    RiskEvent,
    Subreddit,
    TrackingEvent,
    TrackingLink,
    XiaohongshuOpportunity,
)
from .providers import LLMProviderError, provider_for
from .runtime_settings import effective_settings, save_llm_settings
from .schemas import (
    AdminSessionIn,
    AnalyticsOverviewOut,
    BrainOut,
    ConversationOut,
    DecisionOut,
    FollowupIn,
    LLMSettingsOut,
    LLMSettingsUpdate,
    LLMTestOut,
    OpportunityOut,
    ProductBrainData,
    ProductCreate,
    ProductOrderUpdate,
    ProductOut,
    ProductSubredditPatch,
    ProductUpdate,
    RedditAccountCreate,
    RedditAccountOut,
    ReplyOut,
    SourceOut,
    SubredditOut,
    TrackingEventIn,
    XiaohongshuSearchIn,
)
from .services import (
    add_followup,
    build_brain,
    discover_subreddits,
    generate_reply,
    publish_or_shadow,
    record_event,
    run_policy,
)
from .xiaohongshu_client import XiaohongshuClient, XiaohongshuError
from .xiaohongshu_service import (
    XiaohongshuTargetError,
    generate_qualifying_drafts,
    import_search_opportunities,
    manually_generate_and_publish_opportunity,
    publish_best_qualifying_opportunity,
)

logger = logging.getLogger(__name__)

LOCAL_HOSTS = {"", "api", "localhost", "test", "testserver", "web", "127.0.0.1", "::1"}
PUBLIC_DEMO_BLOCKED_GETS = {
    "/v1/reddit/accounts",
    "/v1/reddit/oauth/callback",
    "/v1/reddit/oauth/start",
    "/v1/xiaohongshu/account",
    "/v1/xiaohongshu/login/qrcode",
}
ADMIN_SESSION_COOKIE = "growthagent_admin_session"
ADMIN_SESSION_TTL_SECONDS = 30 * 24 * 60 * 60
ADMIN_SESSION_CLOCK_SKEW_SECONDS = 5 * 60
ADMIN_SESSION_PURPOSE = "growthagent-admin-session-v1"


app = FastAPI(title="GrowthAgent Xiaohongshu Growth API", version="0.1.3")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list({"http://localhost:3000", get_settings().app_url.rstrip("/")}),
    allow_methods=["*"],
    allow_headers=["*"],
)


def public_demo_active(request: Request) -> bool:
    settings = get_settings()
    if settings.allow_public_mutations:
        return False
    if settings.public_demo_mode:
        return True
    forwarded_host = request.headers.get("x-forwarded-host", "").split(",", 1)[0].strip()
    hostname = forwarded_host or request.url.hostname or ""
    hostname = hostname.removeprefix("[").split("]", 1)[0].split(":", 1)[0].lower()
    return hostname not in LOCAL_HOSTS and not hostname.endswith(".local")


def admin_session_signature(settings, issued_at: int) -> str:
    message = f"{ADMIN_SESSION_PURPOSE}:{issued_at}".encode()
    digest = hmac.new(
        settings.admin_api_token.strip().encode(), message, hashlib.sha256
    ).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def create_admin_session_cookie(settings, *, issued_at: int | None = None) -> str:
    timestamp = int(time.time()) if issued_at is None else issued_at
    return f"{timestamp}.{admin_session_signature(settings, timestamp)}"


def valid_admin_session_cookie(value: str, settings, *, now: int | None = None) -> bool:
    if not settings.admin_api_token.strip():
        return False
    timestamp_text, separator, supplied_signature = value.partition(".")
    if not separator or not timestamp_text.isdigit() or not supplied_signature:
        return False
    issued_at = int(timestamp_text)
    current_time = int(time.time()) if now is None else now
    if issued_at > current_time + ADMIN_SESSION_CLOCK_SKEW_SECONDS:
        return False
    if current_time - issued_at > ADMIN_SESSION_TTL_SECONDS:
        return False
    expected_signature = admin_session_signature(settings, issued_at)
    return secrets.compare_digest(supplied_signature, expected_signature)


def admin_request_authorized(request: Request, settings) -> bool:
    configured_token = settings.admin_api_token.strip()
    scheme, separator, supplied_token = request.headers.get("authorization", "").partition(" ")
    bearer_authorized = bool(
        configured_token
        and separator
        and scheme.lower() == "bearer"
        and secrets.compare_digest(supplied_token.strip(), configured_token)
    )
    if bearer_authorized:
        return True
    return valid_admin_session_cookie(
        request.cookies.get(ADMIN_SESSION_COOKIE, ""), settings
    )


@app.middleware("http")
async def enforce_public_demo_boundary(request: Request, call_next):
    demo_active = public_demo_active(request)
    settings = get_settings()
    demo_restricted = demo_active and not admin_request_authorized(request, settings)
    blocked_get = request.method in {"GET", "HEAD"} and request.url.path in PUBLIC_DEMO_BLOCKED_GETS
    managed_gateway_post = (
        request.method == "POST"
        and request.url.path == "/v1/managed-llm/chat/completions"
        and settings.managed_llm_gateway_enabled
    )
    admin_session_mutation = (
        request.url.path == "/v1/admin/session"
        and request.method in {"POST", "DELETE"}
    )
    if demo_restricted and (
        (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and not managed_gateway_post
            and not admin_session_mutation
        )
        or blocked_get
    ):
        return JSONResponse(
            status_code=403,
            content={"detail": "公开演示实例为只读模式，请在本机自托管后使用此功能。"},
            headers={"x-growthagent-demo-mode": "read-only"},
        )
    response = await call_next(request)
    if demo_restricted:
        response.headers["x-growthagent-demo-mode"] = "read-only"
    return response


@app.get("/v1/admin/session")
async def get_admin_session(request: Request):
    return {"authenticated": admin_request_authorized(request, get_settings())}


@app.post("/v1/admin/session")
async def create_admin_session(
    request: Request, response: Response, body: AdminSessionIn
):
    settings = get_settings()
    configured_token = settings.admin_api_token.strip()
    if not configured_token or not secrets.compare_digest(body.token.strip(), configured_token):
        raise HTTPException(401, "授权链接无效或已失效")
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip()
    secure = (
        forwarded_proto.lower() == "https"
        or request.url.scheme == "https"
        or settings.app_url.lower().startswith("https://")
    )
    response.set_cookie(
        key=ADMIN_SESSION_COOKIE,
        value=create_admin_session_cookie(settings),
        max_age=ADMIN_SESSION_TTL_SECONDS,
        httponly=True,
        secure=secure,
        samesite="strict",
        path="/",
    )
    return {"authenticated": True, "expires_in": ADMIN_SESSION_TTL_SECONDS}


@app.delete("/v1/admin/session")
async def delete_admin_session(request: Request, response: Response):
    settings = get_settings()
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip()
    secure = (
        forwarded_proto.lower() == "https"
        or request.url.scheme == "https"
        or settings.app_url.lower().startswith("https://")
    )
    response.delete_cookie(
        key=ADMIN_SESSION_COOKIE,
        httponly=True,
        secure=secure,
        samesite="strict",
        path="/",
    )
    return {"authenticated": False}


@app.get("/health")
async def health(request: Request):
    settings = get_settings()
    llm_ready = bool(
        settings.llm_provider != "mock"
        and settings.llm_api_key
        and settings.llm_strong_model
    )
    return {
        "status": "ok",
        "public_demo": public_demo_active(request),
        "mode": "guarded_auto",
        "autopublish": not settings.global_kill_switch,
        "autopublish_scope": "per_product",
        "kill_switch": settings.global_kill_switch,
        "llm_ready": llm_ready,
        "llm_managed": settings.llm_settings_locked,
        "managed_gateway_ready": managed_gateway_ready(settings),
        "xiaohongshu_login_required": True,
    }


@app.get("/ready")
async def ready(db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url)
    try:
        await db.execute(text("SELECT 1"))
        await redis.ping()
    except Exception as error:
        logger.warning("Readiness check failed: %s", type(error).__name__)
        raise HTTPException(503, "依赖服务尚未就绪") from error
    finally:
        await redis.aclose()
    return {"status": "ready", "database": "ok", "redis": "ok"}


def llm_settings_response(settings, *, editable: bool, testable: bool) -> LLMSettingsOut:
    key = settings.llm_api_key or ""
    managed = settings.llm_settings_locked
    ready = bool(settings.llm_provider != "mock" and key and settings.llm_strong_model)
    return LLMSettingsOut(
        provider=settings.llm_provider,
        base_url=settings.llm_base_url,
        model=settings.llm_strong_model,
        enable_thinking=settings.llm_enable_thinking,
        api_key_configured=bool(key),
        api_key_hint=f"••••{key[-4:]}" if key and not managed else None,
        display_name=settings.llm_display_name,
        ready=ready,
        managed=managed,
        editable=editable,
        testable=testable and ready,
    )


@app.get("/v1/settings/llm", response_model=LLMSettingsOut)
async def get_llm_settings(request: Request, db: AsyncSession = Depends(get_db)):
    settings = await effective_settings(db)
    base_settings = get_settings()
    public_demo = public_demo_active(request) and not admin_request_authorized(
        request, base_settings
    )
    return llm_settings_response(
        settings,
        editable=not settings.llm_settings_locked and not public_demo,
        testable=not public_demo,
    )


@app.put("/v1/settings/llm", response_model=LLMSettingsOut)
async def update_llm_settings(
    request: Request, body: LLMSettingsUpdate, db: AsyncSession = Depends(get_db)
):
    if get_settings().llm_settings_locked:
        raise HTTPException(403, "模型服务由系统统一配置，无需用户修改")
    current = await effective_settings(db)
    api_key = "" if body.clear_api_key else (body.api_key or current.llm_api_key)
    if body.provider != "mock" and (not api_key or not body.model.strip()):
        raise HTTPException(422, "在线模型需要 API Key 和模型名称")
    payload = {
        "llm_provider": body.provider,
        "llm_api_key": api_key,
        "llm_base_url": str(body.base_url).rstrip("/"),
        "llm_strong_model": body.model.strip(),
        "llm_enable_thinking": body.enable_thinking,
    }
    await save_llm_settings(db, payload)
    return llm_settings_response(
        await effective_settings(db),
        editable=not (
            public_demo_active(request)
            and not admin_request_authorized(request, get_settings())
        ),
        testable=not (
            public_demo_active(request)
            and not admin_request_authorized(request, get_settings())
        ),
    )


@app.post("/v1/settings/llm/test", response_model=LLMTestOut)
async def test_llm_settings(db: AsyncSession = Depends(get_db)):
    settings = await effective_settings(db)
    if settings.llm_provider == "mock":
        return LLMTestOut(ok=True, message="Mock 模式可用，不会调用外部模型。")
    try:
        await provider_for(settings).generate_text("只回复 OK")
    except (LLMProviderError, ValueError) as error:
        raise HTTPException(422, str(error)) from error
    return LLMTestOut(ok=True, message="模型连接成功。")


@app.post("/v1/managed-llm/chat/completions")
async def managed_llm_chat(request: Request):
    return await forward_managed_chat(request, get_settings())


async def xhs_call(method: str):
    client = XiaohongshuClient()
    try:
        return await getattr(client, method)()
    except XiaohongshuError as error:
        raise HTTPException(503, str(error)) from error
    finally:
        await client.close()


@app.get("/v1/xiaohongshu/status")
async def xiaohongshu_status():
    return await xhs_call("login_status")


@app.get("/v1/xiaohongshu/login/qrcode")
async def xiaohongshu_qrcode():
    return await xhs_call("login_qrcode")


@app.get("/v1/xiaohongshu/account")
async def xiaohongshu_account():
    return await xhs_call("me")


@app.delete("/v1/xiaohongshu/login")
async def xiaohongshu_logout():
    return await xhs_call("reset_login")


@app.post("/v1/products/{product_id}/xiaohongshu/search", response_model=list[OpportunityOut])
async def search_xiaohongshu(
    product_id: str, body: XiaohongshuSearchIn, db: AsyncSession = Depends(get_db)
):
    product = await get_product(product_id, db)
    client = XiaohongshuClient()
    settings = await effective_settings(db)
    provider = provider_for(settings)
    try:
        imported = await import_search_opportunities(
            db, product_id, client, body.keyword.strip(), provider, detail_limit=body.detail_limit
        )
    except XiaohongshuError as error:
        raise HTTPException(503, str(error)) from error
    finally:
        await client.close()
    await generate_qualifying_drafts(
        db,
        list({row.id for row in imported}),
        provider,
        threshold=product.auto_score_threshold,
        risk_threshold=product.auto_risk_threshold,
    )
    if product.autopublish_enabled:
        client = XiaohongshuClient()
        try:
            await publish_best_qualifying_opportunity(
                db,
                product,
                client,
                kill_switch=settings.global_kill_switch,
                opportunity_ids=list({row.id for row in imported}),
            )
        except (XiaohongshuError, XiaohongshuTargetError) as error:
            logger.warning("Manual search publish step skipped: %s", error)
        finally:
            await client.close()
    rows = list(
        (
            await db.scalars(
                select(XiaohongshuOpportunity)
                .options(selectinload(XiaohongshuOpportunity.content))
                .where(XiaohongshuOpportunity.product_id == product_id)
                .order_by(XiaohongshuOpportunity.opportunity_score.desc())
            )
        ).all()
    )
    return [xiaohongshu_opportunity_out(row) for row in rows]


@app.post("/v1/products/{product_id}/xiaohongshu/auto-search", response_model=list[OpportunityOut])
async def auto_search_xiaohongshu(
    product_id: str, db: AsyncSession = Depends(get_db)
):
    settings = await effective_settings(db)
    try:
        await run_product_automation(
            db,
            product_id,
            provider_for(settings),
            settings,
            force=True,
        )
    except AutomationError as error:
        detail = str(error)
        status = 409 if "登录" in detail or "停止开关" in detail else 503
        raise HTTPException(status, detail) from error
    rows = list(
        (
            await db.scalars(
                select(XiaohongshuOpportunity)
                .options(selectinload(XiaohongshuOpportunity.content))
                .where(XiaohongshuOpportunity.product_id == product_id)
                .order_by(XiaohongshuOpportunity.opportunity_score.desc())
            )
        ).all()
    )
    return [xiaohongshu_opportunity_out(row) for row in rows]


@app.post("/v1/products", response_model=ProductOut, status_code=201)
async def create_product(body: ProductCreate, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    max_order = await db.scalar(
        select(func.max(Product.sort_order)).where(Product.deleted_at.is_(None))
    )
    product = Product(
        name=body.name,
        website_url=str(body.website_url) if body.website_url else None,
        github_url=str(body.github_url) if body.github_url else None,
        daily_reply_limit=min(body.daily_reply_limit, 2, settings.max_daily_reply_limit),
        autopublish_enabled=True,
        is_owned=True,
        disclosure_template="自家做的",
        auto_score_threshold=settings.xiaohongshu_auto_score_threshold,
        auto_risk_threshold=settings.xiaohongshu_auto_risk_threshold,
        search_interval_hours=settings.xiaohongshu_search_interval_hours,
        min_publish_interval_hours=settings.xiaohongshu_min_publish_interval_hours,
        keywords_per_run=settings.xiaohongshu_keywords_per_run,
        details_per_keyword=settings.xiaohongshu_details_per_keyword,
        next_auto_search_at=datetime.now(timezone.utc),
        sort_order=(max_order if max_order is not None else -1) + 1,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@app.get("/v1/products", response_model=list[ProductOut])
async def products(db: AsyncSession = Depends(get_db)):
    return list(
        (
            await db.scalars(
                select(Product)
                .where(Product.deleted_at.is_(None))
                .order_by(Product.sort_order, Product.created_at)
            )
        ).all()
    )


@app.get("/v1/products/trash", response_model=list[ProductOut])
async def trashed_products(db: AsyncSession = Depends(get_db)):
    return list(
        (
            await db.scalars(
                select(Product)
                .where(Product.deleted_at.is_not(None))
                .order_by(Product.deleted_at.desc())
            )
        ).all()
    )


@app.put("/v1/products/order", response_model=list[ProductOut])
async def reorder_products(body: ProductOrderUpdate, db: AsyncSession = Depends(get_db)):
    active = list(
        (
            await db.scalars(select(Product).where(Product.deleted_at.is_(None)).with_for_update())
        ).all()
    )
    if len(body.product_ids) != len(set(body.product_ids)) or set(body.product_ids) != {
        product.id for product in active
    }:
        raise HTTPException(409, "产品列表已发生变化，请刷新后重试")
    by_id = {product.id: product for product in active}
    for position, product_id in enumerate(body.product_ids):
        by_id[product_id].sort_order = position
    await db.commit()
    return [by_id[product_id] for product_id in body.product_ids]


async def get_product(product_id: str, db: AsyncSession):
    product = await db.get(Product, product_id)
    if not product or product.deleted_at is not None:
        raise HTTPException(404, "Product not found")
    return product


@app.delete("/v1/products/{product_id}", response_model=ProductOut)
async def delete_product(product_id: str, db: AsyncSession = Depends(get_db)):
    product = await get_product(product_id, db)
    deleted_at = datetime.now(timezone.utc)
    product.deleted_at = deleted_at
    product.purge_after = deleted_at + timedelta(days=7)
    product.status = "PAUSED"
    product.autopublish_enabled = False
    await db.commit()
    await db.refresh(product)
    return product


@app.post("/v1/products/{product_id}/restore", response_model=ProductOut)
async def restore_product(product_id: str, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product or product.deleted_at is None:
        raise HTTPException(404, "回收站中未找到该产品")
    max_order = await db.scalar(
        select(func.max(Product.sort_order)).where(Product.deleted_at.is_(None))
    )
    product.deleted_at = None
    product.purge_after = None
    product.sort_order = (max_order if max_order is not None else -1) + 1
    await db.commit()
    await db.refresh(product)
    return product


@app.delete("/v1/products/{product_id}/permanent")
async def permanently_delete_product(product_id: str, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    if product.deleted_at is None:
        raise HTTPException(409, "产品必须先移入回收站")
    await db.delete(product)
    await db.commit()
    return {"status": "deleted"}


@app.get("/v1/products/{product_id}", response_model=ProductOut)
async def product(product_id: str, db: AsyncSession = Depends(get_db)):
    return await get_product(product_id, db)


@app.patch("/v1/products/{product_id}", response_model=ProductOut)
async def patch_product(product_id: str, body: ProductUpdate, db: AsyncSession = Depends(get_db)):
    product = await get_product(product_id, db)
    changes = body.model_dump(exclude_unset=True)
    website_url = changes.get("website_url", product.website_url)
    github_url = changes.get("github_url", product.github_url)
    if not website_url and not github_url:
        raise HTTPException(422, "请至少保留产品网站或 GitHub 仓库地址")
    for key, value in changes.items():
        setattr(product, key, str(value) if key.endswith("_url") and value is not None else value)
    await db.commit()
    await db.refresh(product)
    return product


@app.post("/v1/products/{product_id}/ingest", response_model=list[SourceOut])
async def ingest(product_id: str, db: AsyncSession = Depends(get_db)):
    product = await get_product(product_id, db)
    items = []
    if product.website_url:
        items += await ingest_url(product.website_url)
    if product.github_url:
        items += await ingest_url(product.github_url, github=True)
    if not items:
        raise HTTPException(422, "No readable public sources found")
    saved = []
    for item in items:
        existing = await db.scalar(
            select(ProductSource).where(
                ProductSource.product_id == product.id,
                ProductSource.url == item["url"],
                ProductSource.content_hash == item["content_hash"],
            )
        )
        if existing:
            saved.append(existing)
            continue
        source = ProductSource(
            product_id=product.id,
            source_type=item["type"],
            url=item["url"],
            title=item["title"],
            content=item["content"],
            content_hash=item["content_hash"],
        )
        db.add(source)
        saved.append(source)
    product.status = "INGESTED"
    await db.commit()
    for source in saved:
        await db.refresh(source)
    return saved


@app.post("/v1/products/{product_id}/build-brain", response_model=BrainOut)
async def brain_build(product_id: str, db: AsyncSession = Depends(get_db)):
    product = await get_product(product_id, db)
    try:
        version = await build_brain(db, product, provider_for(await effective_settings(db)))
    except LLMProviderError as exc:
        product.status = "ANALYSIS_FAILED"
        await db.commit()
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        logger.exception("Product Brain provider failed for product %s", product_id)
        await db.rollback()
        product = await db.get(Product, product_id)
        if product:
            product.status = "ANALYSIS_FAILED"
            await db.commit()
        raise HTTPException(503, "模型服务暂时不可用，请稍后重试") from exc
    return BrainOut(id=version.id, version=version.version, brain=version.brain_json)


@app.get("/v1/products/{product_id}/brain", response_model=BrainOut)
async def brain_get(product_id: str, db: AsyncSession = Depends(get_db)):
    await get_product(product_id, db)
    version = await db.scalar(
        select(ProductBrainVersion)
        .where(ProductBrainVersion.product_id == product_id, ProductBrainVersion.is_current)
        .order_by(ProductBrainVersion.version.desc())
    )
    if not version:
        raise HTTPException(404, "Product Brain not built")
    return BrainOut(id=version.id, version=version.version, brain=version.brain_json)


@app.patch("/v1/products/{product_id}/brain", response_model=BrainOut)
async def brain_patch(product_id: str, body: ProductBrainData, db: AsyncSession = Depends(get_db)):
    await get_product(product_id, db)
    version = await db.scalar(
        select(ProductBrainVersion)
        .where(ProductBrainVersion.product_id == product_id, ProductBrainVersion.is_current)
        .order_by(ProductBrainVersion.version.desc())
    )
    if not version:
        raise HTTPException(404, "Product Brain not built")
    version.brain_json = body.model_dump()
    await db.commit()
    await db.refresh(version)
    return BrainOut(id=version.id, version=version.version, brain=version.brain_json)


def xiaohongshu_opportunity_out(row: XiaohongshuOpportunity) -> OpportunityOut:
    content = row.content
    note_id = content.parent_content_id or content.platform_content_id
    return OpportunityOut(
        id=row.id,
        status=row.status,
        subreddit="小红书",
        title=content.title or ("用户评论" if content.target_type == "COMMENT" else "小红书笔记"),
        body=content.body,
        permalink=f"https://www.xiaohongshu.com/explore/{note_id}",
        intent_label=(
            "SEEKING_RECOMMENDATION"
            if row.opportunity_score >= 0.7
            else "GENERAL_DISCUSSION"
        ),
        intent_confidence=row.opportunity_score,
        opportunity_score=row.opportunity_score,
        risk_score=row.risk_score,
        recall_sources=[content.source_keyword, content.target_type],
        publish_status=row.status if row.status == "COMMENTED" else None,
        generated_reply=row.draft_body,
        target_type=content.target_type,
        author_name=content.author_name,
        score_reason=row.score_reason,
        match_signals=row.match_signals or [],
        publish_error=row.publish_error,
    )


@app.get("/v1/products/{product_id}/opportunities", response_model=list[OpportunityOut])
async def opportunities(product_id: str, db: AsyncSession = Depends(get_db)):
    await get_product(product_id, db)
    xhs_rows = (
        await db.scalars(
            select(XiaohongshuOpportunity)
            .options(selectinload(XiaohongshuOpportunity.content))
            .where(XiaohongshuOpportunity.product_id == product_id)
            .order_by(XiaohongshuOpportunity.opportunity_score.desc())
        )
    ).all()
    if xhs_rows:
        return [xiaohongshu_opportunity_out(row) for row in xhs_rows]
    rows = (
        await db.scalars(
            select(Candidate)
            .options(selectinload(Candidate.content))
            .where(Candidate.product_id == product_id)
            .order_by(Candidate.opportunity_score.desc())
        )
    ).all()
    out = []
    for x in rows:
        decision = await db.scalar(
            select(PolicyDecision)
            .where(PolicyDecision.candidate_id == x.id)
            .order_by(PolicyDecision.created_at.desc())
        )
        reply = await db.scalar(
            select(GeneratedReply)
            .where(GeneratedReply.candidate_id == x.id)
            .order_by(GeneratedReply.created_at.desc())
        )
        pub = await db.scalar(
            select(PublishedReply)
            .where(PublishedReply.candidate_id == x.id)
            .order_by(PublishedReply.last_checked_at.desc())
        )
        out.append(
            OpportunityOut(
                id=x.id,
                status=x.status,
                subreddit=x.content.subreddit,
                title=x.content.title,
                body=x.content.body,
                permalink=x.content.permalink,
                intent_label=x.intent_label,
                intent_confidence=x.intent_confidence,
                opportunity_score=x.opportunity_score,
                risk_score=x.risk_score,
                recall_sources=x.recall_sources,
                policy_decision=decision.decision if decision else None,
                generated_reply=reply.body if reply else None,
                publish_status=pub.status if pub else None,
            )
        )
    return out


@app.post(
    "/v1/xiaohongshu/opportunities/{opportunity_id}/generate-and-publish",
    response_model=OpportunityOut,
)
async def generate_and_publish_xiaohongshu_opportunity(
    opportunity_id: str, db: AsyncSession = Depends(get_db)
):
    client = XiaohongshuClient()
    try:
        row = await manually_generate_and_publish_opportunity(
            db,
            opportunity_id,
            provider_for(await effective_settings(db)),
            client,
        )
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    except (XiaohongshuError, XiaohongshuTargetError) as error:
        raise HTTPException(503, str(error)) from error
    finally:
        await client.close()
    return xiaohongshu_opportunity_out(row)


@app.get("/v1/opportunities/{candidate_id}", response_model=OpportunityOut)
async def opportunity(candidate_id: str, db: AsyncSession = Depends(get_db)):
    c = await db.get(Candidate, candidate_id)
    if not c:
        raise HTTPException(404, "Opportunity not found")
    await db.refresh(c, ["content"])
    decision = await db.scalar(
        select(PolicyDecision)
        .where(PolicyDecision.candidate_id == c.id)
        .order_by(PolicyDecision.created_at.desc())
    )
    reply = await db.scalar(
        select(GeneratedReply)
        .where(GeneratedReply.candidate_id == c.id)
        .order_by(GeneratedReply.created_at.desc())
    )
    pub = await db.scalar(
        select(PublishedReply)
        .where(PublishedReply.candidate_id == c.id)
        .order_by(PublishedReply.last_checked_at.desc())
    )
    return OpportunityOut(
        id=c.id,
        status=c.status,
        subreddit=c.content.subreddit,
        title=c.content.title,
        body=c.content.body,
        permalink=c.content.permalink,
        intent_label=c.intent_label,
        intent_confidence=c.intent_confidence,
        opportunity_score=c.opportunity_score,
        risk_score=c.risk_score,
        recall_sources=c.recall_sources,
        policy_decision=decision.decision if decision else None,
        generated_reply=reply.body if reply else None,
        publish_status=pub.status if pub else None,
    )


@app.get("/v1/opportunities/{candidate_id}/decision", response_model=DecisionOut)
async def opportunity_decision(candidate_id: str, db: AsyncSession = Depends(get_db)):
    candidate = await db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(404, "Opportunity not found")
    decision = await db.scalar(
        select(PolicyDecision)
        .where(PolicyDecision.candidate_id == candidate_id)
        .order_by(PolicyDecision.created_at.desc())
    )
    if not decision:
        decision = await run_policy(db, candidate, get_settings())
    return DecisionOut(
        id=decision.id,
        decision=decision.decision,
        reply_mode=decision.reply_mode,
        link_policy=decision.link_policy,
        required_disclosure=decision.required_disclosure,
        reason_codes=decision.reason_codes,
    )


@app.get("/v1/opportunities/{candidate_id}/generated-reply", response_model=ReplyOut)
async def opportunity_reply(candidate_id: str, db: AsyncSession = Depends(get_db)):
    candidate = await db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(404, "Opportunity not found")
    decision = await db.scalar(
        select(PolicyDecision)
        .where(PolicyDecision.candidate_id == candidate_id)
        .order_by(PolicyDecision.created_at.desc())
    ) or await run_policy(db, candidate, get_settings())
    reply = await db.scalar(
        select(GeneratedReply)
        .where(GeneratedReply.candidate_id == candidate_id)
        .order_by(GeneratedReply.created_at.desc())
    )
    if not reply:
        reply = await generate_reply(db, candidate, decision)
    return ReplyOut(id=reply.id, body=reply.body, status=reply.status, quality=reply.quality_json)


@app.post("/v1/opportunities/{candidate_id}/publish")
async def opportunity_publish(
    candidate_id: str, force_shadow: bool = False, db: AsyncSession = Depends(get_db)
):
    candidate = await db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(404, "Opportunity not found")
    pub = await publish_or_shadow(db, candidate, get_settings(), force_shadow=force_shadow)
    return {"id": pub.id, "status": pub.status, "idempotency_key": pub.idempotency_key}


@app.post("/v1/products/{product_id}/start")
async def start(product_id: str, db: AsyncSession = Depends(get_db)):
    product = await get_product(product_id, db)
    product.status = "SHADOW_RUNNING"
    await db.commit()
    return {"status": product.status, "autopublish": False, "reason": "MVP runs in shadow mode"}


@app.post("/v1/products/{product_id}/pause")
async def pause(product_id: str, db: AsyncSession = Depends(get_db)):
    product = await get_product(product_id, db)
    product.status = "PAUSED"
    await db.commit()
    return {"status": "PAUSED"}


@app.get("/v1/reddit/oauth/start")
async def reddit_oauth_start():
    settings = get_settings()
    if not settings.reddit_client_id:
        return {
            "status": "configuration_required",
            "message": "Set REDDIT_CLIENT_ID before connecting a real Reddit account.",
        }
    return {
        "authorization_url": f"https://www.reddit.com/api/v1/authorize?client_id={settings.reddit_client_id}&response_type=code&state=local&redirect_uri={settings.reddit_redirect_uri}&duration=permanent&scope=identity,read,submit"
    }


@app.get("/v1/reddit/oauth/callback")
async def reddit_oauth_callback(code: str | None = None, state: str | None = None):
    return {
        "status": "received",
        "code_present": bool(code),
        "state": state,
        "message": "Token exchange is intentionally not performed until credentials are configured.",
    }


@app.post("/v1/reddit/accounts", response_model=RedditAccountOut, status_code=201)
async def reddit_account_create(body: RedditAccountCreate, db: AsyncSession = Depends(get_db)):
    account = RedditAccount(
        username=body.username, status=body.status, app_approval_status=body.app_approval_status
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@app.get("/v1/reddit/accounts", response_model=list[RedditAccountOut])
async def reddit_accounts(db: AsyncSession = Depends(get_db)):
    return list(
        (await db.scalars(select(RedditAccount).order_by(RedditAccount.created_at.desc()))).all()
    )


@app.delete("/v1/reddit/accounts/{account_id}")
async def reddit_account_delete(account_id: str, db: AsyncSession = Depends(get_db)):
    account = await db.get(RedditAccount, account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    await db.delete(account)
    await db.commit()
    return {"status": "deleted"}


@app.post("/v1/products/{product_id}/discover-subreddits", response_model=list[SubredditOut])
async def product_discover_subreddits(product_id: str, db: AsyncSession = Depends(get_db)):
    product = await get_product(product_id, db)
    rows = await discover_subreddits(db, product)
    return [
        SubredditOut(
            id=x.subreddit.id,
            name=x.subreddit.name,
            status=x.status,
            community_score=x.community_score,
            promotion_tolerance=x.promotion_tolerance,
            risk_score=x.risk_score,
            rules=x.subreddit.rules_json,
        )
        for x in rows
    ]


@app.get("/v1/products/{product_id}/subreddits", response_model=list[SubredditOut])
async def product_subreddits(product_id: str, db: AsyncSession = Depends(get_db)):
    await get_product(product_id, db)
    rows = (
        await db.scalars(
            select(ProductSubreddit)
            .options(selectinload(ProductSubreddit.subreddit))
            .where(ProductSubreddit.product_id == product_id)
            .order_by(ProductSubreddit.community_score.desc())
        )
    ).all()
    return [
        SubredditOut(
            id=x.subreddit.id,
            name=x.subreddit.name,
            status=x.status,
            community_score=x.community_score,
            promotion_tolerance=x.promotion_tolerance,
            risk_score=x.risk_score,
            rules=x.subreddit.rules_json,
        )
        for x in rows
    ]


@app.patch("/v1/products/{product_id}/subreddits/{subreddit_id}", response_model=SubredditOut)
async def patch_product_subreddit(
    product_id: str,
    subreddit_id: str,
    body: ProductSubredditPatch,
    db: AsyncSession = Depends(get_db),
):
    row = await db.scalar(
        select(ProductSubreddit).where(
            ProductSubreddit.product_id == product_id, ProductSubreddit.subreddit_id == subreddit_id
        )
    )
    if not row:
        raise HTTPException(404, "Product subreddit not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    await db.commit()
    await db.refresh(row, ["subreddit"])
    return SubredditOut(
        id=row.subreddit.id,
        name=row.subreddit.name,
        status=row.status,
        community_score=row.community_score,
        promotion_tolerance=row.promotion_tolerance,
        risk_score=row.risk_score,
        rules=row.subreddit.rules_json,
    )


@app.post(
    "/v1/products/{product_id}/subreddits/{subreddit_id}/refresh-rules", response_model=SubredditOut
)
async def refresh_rules(product_id: str, subreddit_id: str, db: AsyncSession = Depends(get_db)):
    row = await db.scalar(
        select(ProductSubreddit).where(
            ProductSubreddit.product_id == product_id, ProductSubreddit.subreddit_id == subreddit_id
        )
    )
    if not row:
        raise HTTPException(404, "Product subreddit not found")
    sub = await db.get(Subreddit, subreddit_id)
    sub.rules_json = {
        "promotion": "Unknown; verify subreddit sidebar before autopublish.",
        "refreshed_by": "local_stub",
    }
    await db.commit()
    await db.refresh(row, ["subreddit"])
    return SubredditOut(
        id=row.subreddit.id,
        name=row.subreddit.name,
        status=row.status,
        community_score=row.community_score,
        promotion_tolerance=row.promotion_tolerance,
        risk_score=row.risk_score,
        rules=row.subreddit.rules_json,
    )


@app.get("/v1/products/{product_id}/conversations", response_model=list[ConversationOut])
async def conversations(product_id: str, db: AsyncSession = Depends(get_db)):
    await get_product(product_id, db)
    rows = (
        await db.scalars(
            select(Conversation)
            .where(Conversation.product_id == product_id)
            .order_by(Conversation.last_activity_at.desc())
        )
    ).all()
    return rows


@app.get("/v1/conversations/{conversation_id}", response_model=ConversationOut)
async def conversation_get(conversation_id: str, db: AsyncSession = Depends(get_db)):
    row = await db.get(Conversation, conversation_id)
    if not row:
        raise HTTPException(404, "Conversation not found")
    return row


@app.post("/v1/conversations/{conversation_id}/followup", response_model=ConversationOut)
async def conversation_followup(
    conversation_id: str, body: FollowupIn, db: AsyncSession = Depends(get_db)
):
    row = await db.get(Conversation, conversation_id)
    if not row:
        raise HTTPException(404, "Conversation not found")
    return await add_followup(db, row, body.body, get_settings())


@app.post("/v1/conversations/{conversation_id}/stop")
async def conversation_stop(conversation_id: str, db: AsyncSession = Depends(get_db)):
    row = await db.get(Conversation, conversation_id)
    if not row:
        raise HTTPException(404, "Conversation not found")
    row.state = "CLOSED"
    row.closed_reason = "MANUAL_STOP"
    await db.commit()
    return {"status": "CLOSED"}


@app.get("/v1/products/{product_id}/analytics/overview", response_model=AnalyticsOverviewOut)
async def analytics_overview(product_id: str, db: AsyncSession = Depends(get_db)):
    await get_product(product_id, db)
    scanned = (
        await db.scalar(
            select(func.count()).select_from(Candidate).where(Candidate.product_id == product_id)
        )
        or 0
    )
    qualified = (
        await db.scalar(
            select(func.count())
            .select_from(Candidate)
            .where(
                Candidate.product_id == product_id,
                Candidate.opportunity_score >= 0.4,
                Candidate.risk_score < 0.5,
            )
        )
        or 0
    )
    conv = (
        await db.scalar(
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.product_id == product_id)
        )
        or 0
    )
    waiting = (
        await db.scalar(
            select(func.count())
            .select_from(Conversation)
            .where(
                Conversation.product_id == product_id,
                Conversation.state.in_(["POSTED", "USER_ENGAGED"]),
            )
        )
        or 0
    )
    visits = (
        await db.scalar(
            select(func.count())
            .select_from(TrackingEvent)
            .where(
                TrackingEvent.product_id == product_id,
                TrackingEvent.event_name.in_(
                    ["page_view", "session_started", "attribution_received"]
                ),
            )
        )
        or 0
    )
    signups = (
        await db.scalar(
            select(func.count())
            .select_from(TrackingEvent)
            .where(TrackingEvent.product_id == product_id, TrackingEvent.event_name == "signup")
        )
        or 0
    )
    activations = (
        await db.scalar(
            select(func.count())
            .select_from(TrackingEvent)
            .where(TrackingEvent.product_id == product_id, TrackingEvent.event_name == "activated")
        )
        or 0
    )
    negatives = (
        await db.scalar(
            select(func.count())
            .select_from(RiskEvent)
            .where(
                RiskEvent.product_id == product_id,
                RiskEvent.event_type.in_(["NEGATIVE_REACTION", "MOD_WARNING"]),
            )
        )
        or 0
    )
    return AnalyticsOverviewOut(
        scanned=scanned,
        candidates=scanned,
        qualified_opportunities=qualified,
        conversations=conv,
        waiting_followups=waiting,
        user_questions=0,
        link_requests=0,
        visits=visits,
        signups=signups,
        activations=activations,
        removals=0,
        negative_interactions=negatives,
        risk_level="HIGH" if negatives else "PROTECTED",
    )


@app.get("/v1/products/{product_id}/analytics/subreddits")
async def analytics_subreddits(product_id: str, db: AsyncSession = Depends(get_db)):
    await get_product(product_id, db)
    candidates = (
        await db.scalars(
            select(Candidate)
            .options(selectinload(Candidate.content))
            .where(Candidate.product_id == product_id)
        )
    ).all()
    totals: dict[str, dict] = {}
    for c in candidates:
        bucket = totals.setdefault(
            c.content.subreddit, {"subreddit": c.content.subreddit, "candidates": 0, "qualified": 0}
        )
        bucket["candidates"] += 1
        if c.opportunity_score >= 0.4 and c.risk_score < 0.5:
            bucket["qualified"] += 1
    return list(totals.values())


@app.get("/v1/products/{product_id}/analytics/intents")
async def analytics_intents(product_id: str, db: AsyncSession = Depends(get_db)):
    await get_product(product_id, db)
    rows = (
        await db.execute(
            select(Candidate.intent_label, func.count())
            .where(Candidate.product_id == product_id)
            .group_by(Candidate.intent_label)
        )
    ).all()
    return [{"intent": intent, "count": count} for intent, count in rows]


@app.get("/v1/products/{product_id}/analytics/reply-strategies")
async def analytics_reply_strategies(product_id: str, db: AsyncSession = Depends(get_db)):
    await get_product(product_id, db)
    rows = (
        await db.execute(
            select(PolicyDecision.reply_mode, PolicyDecision.decision, func.count())
            .join(Candidate)
            .where(Candidate.product_id == product_id)
            .group_by(PolicyDecision.reply_mode, PolicyDecision.decision)
        )
    ).all()
    return [
        {"reply_mode": mode, "decision": decision, "count": count} for mode, decision, count in rows
    ]


@app.post("/v1/events")
async def events(body: TrackingEventIn, request: Request, db: AsyncSession = Depends(get_db)):
    row = await record_event(
        db,
        body.event,
        body.product_id,
        body.short_code,
        body.anonymous_id,
        body.user_id,
        body.properties,
        request.headers.get("user-agent"),
    )
    return {"status": "ok", "id": row.id}


@app.get("/c/{short_code}")
async def tracking_redirect(short_code: str, db: AsyncSession = Depends(get_db)):
    link = await db.scalar(select(TrackingLink).where(TrackingLink.short_code == short_code))
    if not link:
        raise HTTPException(404, "Tracking link not found")
    await record_event(db, "page_view", link.product_id, short_code, None, None, {})
    sep = "&" if "?" in link.destination_url else "?"
    utm = "&".join(f"{k}={v}" for k, v in link.utm_json.items())
    return RedirectResponse(f"{link.destination_url}{sep}{utm}")


@app.get("/v1/tracking/sdk.js", response_class=PlainTextResponse)
async def tracking_sdk():
    return """(function(){var s=document.currentScript,p=s&&s.dataset.project,base=s&&new URL(s.src).origin;function id(){var k='rga_aid',v=localStorage.getItem(k);if(!v){v=crypto.randomUUID();localStorage.setItem(k,v)}return v}window.redditGrowth={track:function(e,props){fetch(base+'/v1/events',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({event:e,product_id:p,anonymous_id:id(),properties:props||{}})});}};window.redditGrowth.track('session_started');})();"""


@app.post("/v1/admin/kill-switch/enable")
async def kill_enable():
    return {
        "status": "requires_env_change",
        "message": "Set GLOBAL_KILL_SWITCH=true and restart services.",
    }


@app.post("/v1/admin/kill-switch/disable")
async def kill_disable():
    return {
        "status": "requires_env_change",
        "message": "Set GLOBAL_KILL_SWITCH=false and restart services.",
    }


@app.post("/v1/products/{product_id}/autopublish/enable", response_model=ProductOut)
async def autopublish_enable(product_id: str, db: AsyncSession = Depends(get_db)):
    product = await get_product(product_id, db)
    product.autopublish_enabled = True
    product.automation_status = "IDLE"
    product.automation_error = None
    product.automation_failures = 0
    product.next_auto_search_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(product)
    return product


@app.post("/v1/products/{product_id}/autopublish/disable", response_model=ProductOut)
async def autopublish_disable(product_id: str, db: AsyncSession = Depends(get_db)):
    product = await get_product(product_id, db)
    product.autopublish_enabled = False
    product.automation_status = "PAUSED"
    await db.commit()
    await db.refresh(product)
    return product


@app.get("/v1/products/{product_id}/risk-events")
async def risk_events(product_id: str, db: AsyncSession = Depends(get_db)):
    await get_product(product_id, db)
    rows = (
        await db.scalars(
            select(RiskEvent)
            .where(RiskEvent.product_id == product_id)
            .order_by(RiskEvent.created_at.desc())
        )
    ).all()
    return [
        {
            "id": x.id,
            "event_type": x.event_type,
            "severity": x.severity,
            "details": x.details,
            "action_taken": x.action_taken,
            "created_at": x.created_at,
        }
        for x in rows
    ]


@app.get("/v1/products/{product_id}/audit-log")
async def audit_log(product_id: str, db: AsyncSession = Depends(get_db)):
    await get_product(product_id, db)
    decisions = (
        await db.scalars(
            select(PolicyDecision)
            .join(Candidate)
            .where(Candidate.product_id == product_id)
            .order_by(PolicyDecision.created_at.desc())
        )
    ).all()
    return [
        {
            "id": x.id,
            "type": "policy_decision",
            "decision": x.decision,
            "reason_codes": x.reason_codes,
            "created_at": x.created_at,
        }
        for x in decisions
    ]
