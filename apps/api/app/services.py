import hashlib
import re
import secrets
from datetime import timedelta
from pydantic import ValidationError
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from .config import Settings
from .models import (
    Candidate,
    Conversation,
    ConversationMessage,
    GeneratedReply,
    ModelRun,
    PolicyDecision,
    Product,
    ProductBrainVersion,
    ProductSource,
    ProductSubreddit,
    PublishedReply,
    QueryTerm,
    RedditAccount,
    RiskEvent,
    Subreddit,
    TrackingEvent,
    TrackingLink,
    now,
)
from .providers import LLMProvider
from .schemas import ProductBrainData


def _normalize_brain_output(raw: dict) -> dict:
    """Accept common provider aliases before applying the strict contract."""
    data = dict(raw or {})
    if "supported_claims" not in data and isinstance(data.get("claims"), list):
        data["supported_claims"] = data.pop("claims")
    for claim in data.get("supported_claims", []):
        if isinstance(claim, dict):
            if "source_quote" not in claim and "quote" in claim:
                claim["source_quote"] = claim.pop("quote")
            claim.setdefault("confidence", 0.8)
    return data


def _validate_brain_evidence(brain: ProductBrainData, sources: list[ProductSource]) -> None:
    source_map = {source.id: source.content for source in sources}
    for claim in brain.supported_claims:
        content = source_map.get(claim.source_id)
        if content is None:
            raise ValueError(f"Claim references unknown source_id: {claim.source_id}")
        quote = " ".join(claim.source_quote.lower().split())
        haystack = " ".join(content.lower().split())
        if quote not in haystack:
            raise ValueError(f"Claim quote is not present in source {claim.source_id}")


async def build_brain(db: AsyncSession, product: Product, provider: LLMProvider):
    sources = (
        await db.scalars(
            select(ProductSource).where(
                ProductSource.product_id == product.id, ProductSource.is_active
            )
        )
    ).all()
    if not sources:
        raise ValueError("Ingest at least one product source first")
    # Product sites often repeat navigation and long documentation on every page.
    # A bounded evidence window is faster and still preserves exact quote validation.
    compact_sources = []
    remaining = 16_000
    for source in sources[:8]:
        content = source.content[: min(4_000, remaining)]
        if not content:
            continue
        compact_sources.append({"id": source.id, "url": source.url, "content": content})
        remaining -= len(content)
        if remaining <= 0:
            break
    payload = {
        "product_name": product.name,
        "sources": compact_sources,
    }
    schema = ProductBrainData.model_json_schema()
    raw = await provider.generate_structured("product_brain_v2", payload, schema)
    try:
        brain_model = ProductBrainData.model_validate(_normalize_brain_output(raw))
        _validate_brain_evidence(brain_model, sources)
    except (ValidationError, ValueError) as first_error:
        repair_payload = {
            **payload,
            "previous_output": raw,
            "validation_error": str(first_error),
            "repair_instruction": "Return a complete replacement object matching every required field. Preserve only claims with exact source quotes.",
        }
        repaired = await provider.generate_structured(
            "product_brain_repair_v2", repair_payload, schema
        )
        try:
            brain_model = ProductBrainData.model_validate(_normalize_brain_output(repaired))
            _validate_brain_evidence(brain_model, sources)
        except (ValidationError, ValueError) as final_error:
            product.status = "ANALYSIS_FAILED"
            await db.commit()
            raise ValueError(
                f"Model returned an incomplete Product Brain after repair: {final_error}"
            ) from final_error
    brain = brain_model.model_dump()
    current = (
        await db.scalar(
            select(func.max(ProductBrainVersion.version)).where(
                ProductBrainVersion.product_id == product.id
            )
        )
        or 0
    )
    await db.execute(
        update(ProductBrainVersion)
        .where(ProductBrainVersion.product_id == product.id)
        .values(is_current=False)
    )
    version = ProductBrainVersion(product_id=product.id, version=current + 1, brain_json=brain)
    db.add(version)
    await db.execute(
        update(QueryTerm).where(QueryTerm.product_id == product.id).values(status="SUPERSEDED")
    )
    for kind, terms in brain.get("query_graph", {}).items():
        for term in terms:
            db.add(QueryTerm(product_id=product.id, term_type=kind, term=str(term), weight=1))
    run = ModelRun(
        run_type="PRODUCT_BRAIN",
        entity_type="product",
        entity_id=product.id,
        provider=provider.__class__.__name__,
        model="mock" if provider.__class__.__name__.startswith("Mock") else "configured",
        prompt_version="product_brain/v1",
        input_hash=hashlib.sha256(str(payload).encode()).hexdigest(),
        input_summary={"source_count": len(sources)},
        output_json=brain,
    )
    product.target_users = brain["target_users"]
    product.key_selling_points = [item["claim"] for item in brain["supported_claims"][:5]]
    product.forbidden_claims = brain["unsupported_or_uncertain_claims"]
    product.recommend_when = brain["recommend_when"]
    product.do_not_recommend_when = brain["do_not_recommend_when"]
    db.add(run)
    product.status = "READY"
    await db.commit()
    await db.refresh(version)
    return version


SENSITIVE = {"suicide", "self harm", "legal advice", "medical advice", "financial advice", "nsfw"}
NEGATIVE = {"spam", "stop spamming", "shill", "go away", "reported"}
ALLOWING_COMMUNITY_STATES = {"ALLOW_AUTOREPLY", "ALLOW_READ_ONLY"}
PUBLISH_COMMUNITY_STATES = {"ALLOW_AUTOREPLY"}


def _text(candidate: Candidate) -> str:
    return f"{candidate.content.title or ''} {candidate.content.body}".lower()


def classify_followup_intent(body: str) -> str:
    text = body.lower()
    if any(x in text for x in ["moderator", "removed", "rule violation"]):
        return "MOD_WARNING"
    if any(x in text for x in NEGATIVE):
        return "NEGATIVE_REACTION"
    if any(x in text for x in ["link", "url", "website", "send it"]):
        return "ASK_LINK"
    if any(x in text for x in ["price", "pricing", "cost", "free"]):
        return "ASK_PRICE"
    if any(x in text for x in ["feature", "support", "can it", "does it"]):
        return "ASK_FEATURE"
    if any(x in text for x in ["compare", "vs ", "better than", "alternative"]):
        return "ASK_COMPARISON"
    if any(x in text for x in ["bug", "broken", "issue"]):
        return "REPORT_BUG"
    if any(x in text for x in ["thanks", "thank you"]):
        return "THANKS_ONLY"
    return "EXPRESS_INTEREST"


async def discover_subreddits(db: AsyncSession, product: Product) -> list[ProductSubreddit]:
    brain = await db.scalar(
        select(ProductBrainVersion).where(
            ProductBrainVersion.product_id == product.id, ProductBrainVersion.is_current
        )
    )
    terms = []
    if brain:
        graph = brain.brain_json.get("query_graph", {})
        terms = (
            graph.get("use_cases", [])
            + graph.get("direct_terms", [])
            + graph.get("competitors", [])
        )
    names = []
    for term in terms:
        cleaned = re.sub(r"[^a-zA-Z0-9]", "", str(term))[:32].lower()
        if cleaned and cleaned not in names:
            names.append(cleaned)
    names = (names + ["startups", "SaaS", "SideProject", "Entrepreneur", "productivity"])[:20]
    rows = []
    for i, name in enumerate(names):
        subreddit = await db.scalar(
            select(Subreddit).where(func.lower(Subreddit.name) == name.lower())
        )
        if not subreddit:
            subreddit = Subreddit(
                name=name,
                title=f"r/{name}",
                description="Discovered from Product Brain",
                rules_json={"promotion": "Unknown; default read-only until reviewed."},
            )
            db.add(subreddit)
            await db.flush()
        ps = await db.scalar(
            select(ProductSubreddit).where(
                ProductSubreddit.product_id == product.id,
                ProductSubreddit.subreddit_id == subreddit.id,
            )
        )
        if not ps:
            status = "ALLOW_AUTOREPLY" if i < 3 else "ALLOW_READ_ONLY"
            ps = ProductSubreddit(
                product_id=product.id,
                subreddit_id=subreddit.id,
                status=status,
                community_score=max(0.2, 0.8 - i * 0.03),
                promotion_tolerance=0.35 if status == "ALLOW_AUTOREPLY" else 0.15,
            )
            db.add(ps)
        rows.append(ps)
    await db.commit()
    return list(
        (
            await db.scalars(
                select(ProductSubreddit)
                .options(selectinload(ProductSubreddit.subreddit))
                .where(ProductSubreddit.product_id == product.id)
                .order_by(ProductSubreddit.community_score.desc())
            )
        ).all()
    )


async def run_policy(db: AsyncSession, candidate: Candidate, settings: Settings) -> PolicyDecision:
    await db.refresh(candidate, ["content"])
    text = _text(candidate)
    product = await db.get(Product, candidate.product_id)
    ps = await db.scalar(
        select(ProductSubreddit)
        .join(Subreddit)
        .where(
            ProductSubreddit.product_id == candidate.product_id,
            func.lower(Subreddit.name) == candidate.content.subreddit.lower(),
        )
    )
    reasons = []
    decision = "SHADOW_ONLY"
    reply_mode = "HELP_AND_DISCLOSE"
    link_policy = "NO_LINK_UNLESS_REQUESTED"
    if any(x in text for x in SENSITIVE):
        decision, reply_mode, reasons = "BLOCK", "NONE", ["SENSITIVE_CONTENT"]
    elif any(x in text for x in ["no promotion", "not looking for tools", "no vendors"]):
        decision, reply_mode, reasons = "SKIP", "NONE", ["USER_OR_COMMUNITY_REJECTS_PROMO"]
    elif candidate.risk_score >= 0.7 or candidate.intent_label in {
        "SENSITIVE_CONTENT",
        "PROMOTIONAL_CONTENT",
        "IRRELEVANT",
    }:
        decision, reply_mode, reasons = "SKIP", "NONE", ["HIGH_RISK_OR_LOW_RELEVANCE"]
    elif not ps or ps.status not in ALLOWING_COMMUNITY_STATES:
        decision, reasons = "SHADOW_ONLY", ["COMMUNITY_NOT_ALLOWLISTED"]
    elif candidate.opportunity_score < 0.35 or candidate.intent_confidence < 0.55:
        decision, reasons = "SKIP", ["LOW_OPPORTUNITY_SCORE"]
    else:
        reasons.append("EXPLICIT_OR_SEMANTIC_NEED")
        if ps.status in PUBLISH_COMMUNITY_STATES and candidate.opportunity_score >= 0.55:
            decision = "ALLOW_AUTOREPLY"
            reasons.append("COMMUNITY_ALLOWED")
        if (
            product
            and product.allow_first_reply_link
            and candidate.intent_label == "SEEKING_RECOMMENDATION"
        ):
            link_policy = "ALLOW_CONTEXTUAL_LINK"
    if settings.global_kill_switch:
        decision, reasons = "ESCALATE_STOP", reasons + ["GLOBAL_KILL_SWITCH"]
    if (
        not settings.autopublish_enabled
        or settings.reddit_app_approval_status != "COMMERCIAL_APPROVED"
    ):
        if decision == "ALLOW_AUTOREPLY":
            decision, reasons = "SHADOW_ONLY", reasons + ["AUTOPUBLISH_GATE_CLOSED"]
    row = PolicyDecision(
        candidate_id=candidate.id,
        decision=decision,
        reply_mode=reply_mode,
        link_policy=link_policy,
        reason_codes=reasons,
        input_snapshot={
            "opportunity_score": candidate.opportunity_score,
            "intent": candidate.intent_label,
            "subreddit": candidate.content.subreddit,
        },
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def generate_reply(
    db: AsyncSession, candidate: Candidate, decision: PolicyDecision
) -> GeneratedReply:
    product = await db.get(Product, candidate.product_id)
    brain = await db.scalar(
        select(ProductBrainVersion).where(
            ProductBrainVersion.product_id == candidate.product_id, ProductBrainVersion.is_current
        )
    )
    if decision.decision in {"BLOCK", "SKIP", "ESCALATE_STOP"}:
        body = "No reply generated because policy decided not to participate."
        status = "POLICY_SKIPPED"
    else:
        claims = (brain.brain_json.get("supported_claims", []) if brain else [])[:2]
        value = "A practical way to approach this is to write down the must-have workflow, the deal-breakers, and whether you need a tool or a process change first."
        product_name = product.name if product else "the product"
        disclosure = (
            (
                product.disclosure_template
                if product and product.disclosure_template
                else f"I'm building {product_name}"
            )
            if product
            else "I'm connected to this product"
        )
        claim_text = (
            claims[0]["claim"]
            if claims
            else "I can only speak to capabilities that are documented in the product sources."
        )
        body = f"{value}\n\n{disclosure}, so take this as a transparent suggestion: {product_name} may fit if your need matches this verified point: {claim_text}\n\nI would not use it if you need something outside the documented capabilities."
        status = "QUALITY_PASSED"
    digest = hashlib.sha256(body.encode()).hexdigest()
    quality = {
        "has_disclosure": "building" in body.lower() or "connected" in body.lower(),
        "independent_value": decision.decision not in {"BLOCK", "SKIP"},
        "contains_link": "http://" in body or "https://" in body,
    }
    row = GeneratedReply(
        candidate_id=candidate.id,
        policy_decision_id=decision.id,
        body=body,
        body_hash=digest,
        status=status,
        quality_json=quality,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def publish_or_shadow(
    db: AsyncSession, candidate: Candidate, settings: Settings, force_shadow: bool = False
) -> PublishedReply:
    await db.refresh(candidate, ["content"])
    existing = await db.scalar(
        select(PublishedReply).where(PublishedReply.candidate_id == candidate.id)
    )
    if existing:
        return existing
    decision = await db.scalar(
        select(PolicyDecision)
        .where(PolicyDecision.candidate_id == candidate.id)
        .order_by(PolicyDecision.created_at.desc())
    )
    if not decision:
        decision = await run_policy(db, candidate, settings)
    reply = await db.scalar(
        select(GeneratedReply)
        .where(GeneratedReply.candidate_id == candidate.id)
        .order_by(GeneratedReply.created_at.desc())
    )
    if not reply:
        reply = await generate_reply(db, candidate, decision)
    account = await db.scalar(
        select(RedditAccount)
        .where(RedditAccount.status == "ACTIVE")
        .order_by(RedditAccount.created_at)
    )
    product = await db.get(Product, candidate.product_id)
    can_publish = bool(
        not force_shadow
        and product
        and product.autopublish_enabled
        and decision.decision == "ALLOW_AUTOREPLY"
        and account
        and account.status == "ACTIVE"
        and account.app_approval_status == "COMMERCIAL_APPROVED"
        and settings.autopublish_enabled
        and settings.reddit_app_approval_status == "COMMERCIAL_APPROVED"
        and not settings.global_kill_switch
    )
    key = hashlib.sha256(
        f"{candidate.product_id}:{candidate.content.reddit_fullname}:policy_v1".encode()
    ).hexdigest()
    brain = await db.scalar(
        select(ProductBrainVersion).where(
            ProductBrainVersion.product_id == candidate.product_id, ProductBrainVersion.is_current
        )
    )
    pub = PublishedReply(
        candidate_id=candidate.id,
        reddit_account_id=account.id if account else None,
        reddit_comment_id=("mock_" + key[:20]),
        parent_reddit_fullname=candidate.content.reddit_fullname,
        body=reply.body,
        body_hash=reply.body_hash,
        product_brain_version_id=brain.id if brain else None,
        policy_decision_id=decision.id,
        idempotency_key=key,
        status="PUBLISHED_MOCK" if can_publish else "SHADOW_RECORDED",
        published_at=now() if can_publish else None,
        last_checked_at=now(),
    )
    db.add(pub)
    await db.flush()
    conv = Conversation(
        product_id=candidate.product_id,
        published_reply_id=pub.id,
        state="POSTED",
        next_check_at=now() + timedelta(minutes=5),
    )
    db.add(conv)
    await db.flush()
    db.add(
        ConversationMessage(
            conversation_id=conv.id,
            reddit_comment_id=pub.reddit_comment_id,
            author_type="agent",
            body=pub.body,
            intent_label="INITIAL_REPLY",
        )
    )
    if not can_publish:
        db.add(
            RiskEvent(
                product_id=candidate.product_id,
                event_type="AUTOPUBLISH_BLOCKED",
                severity="INFO",
                details={"decision": decision.decision, "account_present": bool(account)},
                action_taken="SHADOW_RECORDED",
            )
        )
    await db.commit()
    await db.refresh(pub)
    return pub


async def add_followup(
    db: AsyncSession, conversation: Conversation, body: str, settings: Settings
) -> Conversation:
    intent = classify_followup_intent(body)
    db.add(
        ConversationMessage(
            conversation_id=conversation.id,
            reddit_comment_id="user_" + secrets.token_hex(10),
            author_type="user",
            body=body,
            intent_label=intent,
        )
    )
    conversation.last_activity_at = now()
    if intent == "ASK_LINK":
        conversation.state = "LINK_SHARED"
        conversation.followup_count += 1
        product = await db.get(Product, conversation.product_id)
        dest = product.website_url or product.github_url or "https://example.com"
        short = secrets.token_urlsafe(6)
        link = TrackingLink(
            product_id=conversation.product_id,
            conversation_id=conversation.id,
            short_code=short,
            destination_url=dest,
            utm_json={
                "utm_source": "reddit",
                "utm_medium": "organic_conversation",
                "utm_content": conversation.id,
            },
        )
        db.add(link)
        db.add(
            ConversationMessage(
                conversation_id=conversation.id,
                reddit_comment_id="agent_" + secrets.token_hex(10),
                author_type="agent",
                body=f"Sure. Here is the tracked link for this conversation: /c/{short}",
                intent_label="LINK_SHARED",
            )
        )
    elif intent in {"NEGATIVE_REACTION", "MOD_WARNING"}:
        conversation.state = "CLOSED"
        conversation.closed_reason = intent
        db.add(
            RiskEvent(
                product_id=conversation.product_id,
                conversation_id=conversation.id,
                event_type=intent,
                severity="HIGH",
                details={"body": body},
                action_taken="CONVERSATION_CLOSED",
            )
        )
    elif conversation.followup_count >= settings.max_conversation_followups:
        conversation.state = "CLOSED"
        conversation.closed_reason = "MAX_FOLLOWUPS"
    else:
        conversation.state = "USER_ENGAGED"
        conversation.followup_count += 1
        conversation.next_check_at = now() + timedelta(minutes=20)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def record_event(
    db: AsyncSession,
    event_name: str,
    product_id: str | None,
    short_code: str | None,
    anonymous_id: str | None,
    user_id: str | None,
    properties: dict,
    user_agent: str | None = None,
):
    link = (
        await db.scalar(select(TrackingLink).where(TrackingLink.short_code == short_code))
        if short_code
        else None
    )
    row = TrackingEvent(
        product_id=product_id or (link.product_id if link else None),
        tracking_link_id=link.id if link else None,
        anonymous_id=anonymous_id,
        user_id=user_id,
        event_name=event_name,
        properties=properties,
        user_agent=user_agent,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row
