import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value_encrypted: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class Product(Base):
    __tablename__ = "products"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200))
    website_url: Mapped[str | None] = mapped_column(String(2048))
    github_url: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[str] = mapped_column(String(40), default="DRAFT")
    autopublish_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    daily_reply_limit: Mapped[int] = mapped_column(Integer, default=2)
    auto_score_threshold: Mapped[float] = mapped_column(Float, default=0.75)
    auto_risk_threshold: Mapped[float] = mapped_column(Float, default=0.35)
    search_interval_hours: Mapped[int] = mapped_column(Integer, default=3)
    min_publish_interval_hours: Mapped[int] = mapped_column(Integer, default=4)
    keywords_per_run: Mapped[int] = mapped_column(Integer, default=3)
    details_per_keyword: Mapped[int] = mapped_column(Integer, default=2)
    automation_status: Mapped[str] = mapped_column(String(30), default="IDLE")
    automation_error: Mapped[str | None] = mapped_column(Text)
    automation_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_auto_search_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_auto_search_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_auto_publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    allow_first_reply_link: Mapped[bool] = mapped_column(Boolean, default=False)
    disclosure_template: Mapped[str] = mapped_column(String(500), default="")
    is_owned: Mapped[bool] = mapped_column(Boolean, default=False)
    target_users: Mapped[list] = mapped_column(JSON, default=list)
    key_selling_points: Mapped[list] = mapped_column(JSON, default=list)
    forbidden_claims: Mapped[list] = mapped_column(JSON, default=list)
    recommend_when: Mapped[list] = mapped_column(JSON, default=list)
    do_not_recommend_when: Mapped[list] = mapped_column(JSON, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    sources = relationship("ProductSource", cascade="all, delete-orphan")


class RedditAccount(Base):
    __tablename__ = "reddit_accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    reddit_user_id: Mapped[str | None] = mapped_column(String(100))
    oauth_token_encrypted: Mapped[str] = mapped_column(Text, default="")
    refresh_token_encrypted: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="NEEDS_OAUTH")
    app_approval_status: Mapped[str] = mapped_column(String(60), default="DEVELOPMENT_ONLY")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ProductSource(Base):
    __tablename__ = "product_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    source_type: Mapped[str] = mapped_column(String(30))
    url: Mapped[str] = mapped_column(String(2048))
    title: Mapped[str] = mapped_column(String(500), default="")
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("product_id", "url", "content_hash"),)


class ProductBrainVersion(Base):
    __tablename__ = "product_brain_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    brain_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("product_id", "version"),)


class QueryTerm(Base):
    __tablename__ = "query_terms"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    term_type: Mapped[str] = mapped_column(String(40))
    term: Mapped[str] = mapped_column(String(500))
    weight: Mapped[float] = mapped_column(Float, default=1)
    source: Mapped[str] = mapped_column(String(40), default="brain")
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Subreddit(Base):
    __tablename__ = "subreddits"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    rules_json: Mapped[dict] = mapped_column(JSON, default=dict)
    rules_last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProductSubreddit(Base):
    __tablename__ = "product_subreddits"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    subreddit_id: Mapped[str] = mapped_column(
        ForeignKey("subreddits.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(40), default="ALLOW_READ_ONLY")
    community_score: Mapped[float] = mapped_column(Float, default=0.5)
    promotion_tolerance: Mapped[float] = mapped_column(Float, default=0.2)
    risk_score: Mapped[float] = mapped_column(Float, default=0)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_poll_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    subreddit = relationship("Subreddit")
    __table_args__ = (UniqueConstraint("product_id", "subreddit_id"),)


class RedditContent(Base):
    __tablename__ = "reddit_contents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    reddit_fullname: Mapped[str] = mapped_column(String(30), unique=True)
    content_type: Mapped[str] = mapped_column(String(20))
    subreddit: Mapped[str] = mapped_column(String(100), index=True)
    parent_reddit_fullname: Mapped[str | None] = mapped_column(String(30))
    author_name: Mapped[str] = mapped_column(String(100), default="[unknown]")
    title: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    permalink: Mapped[str] = mapped_column(String(2048), default="")
    score: Mapped[int] = mapped_column(Integer, default=0)
    num_comments: Mapped[int] = mapped_column(Integer, default=0)
    created_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    content_hash: Mapped[str] = mapped_column(String(64))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict)


class XiaohongshuContent(Base):
    __tablename__ = "xiaohongshu_contents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    dedupe_key: Mapped[str] = mapped_column(String(300), unique=True, index=True)
    target_type: Mapped[str] = mapped_column(String(20))
    platform_content_id: Mapped[str] = mapped_column(String(120), index=True)
    parent_content_id: Mapped[str | None] = mapped_column(String(120), index=True)
    xsec_token: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    author_id: Mapped[str] = mapped_column(String(120), default="")
    author_name: Mapped[str] = mapped_column(String(200), default="")
    source_keyword: Mapped[str] = mapped_column(String(300), default="")
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class XiaohongshuOpportunity(Base):
    __tablename__ = "xiaohongshu_opportunities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    content_id: Mapped[str] = mapped_column(
        ForeignKey("xiaohongshu_contents.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="DISCOVERED")
    opportunity_score: Mapped[float] = mapped_column(Float, default=0.5)
    risk_score: Mapped[float] = mapped_column(Float, default=0.1)
    score_reason: Mapped[str] = mapped_column(Text, default="")
    match_signals: Mapped[list] = mapped_column(JSON, default=list)
    publish_error: Mapped[str | None] = mapped_column(Text)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    commented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    draft_body: Mapped[str | None] = mapped_column(Text)
    draft_status: Mapped[str | None] = mapped_column(String(30))
    draft_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    content = relationship("XiaohongshuContent")
    __table_args__ = (UniqueConstraint("product_id", "content_id"),)


class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    reddit_content_id: Mapped[str] = mapped_column(
        ForeignKey("reddit_contents.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(30), default="RECALLED")
    recall_sources: Mapped[list] = mapped_column(JSON, default=list)
    bm25_score: Mapped[float] = mapped_column(Float, default=0)
    embedding_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    intent_label: Mapped[str] = mapped_column(String(60), default="GENERAL_DISCUSSION")
    intent_confidence: Mapped[float] = mapped_column(Float, default=0)
    opportunity_score: Mapped[float] = mapped_column(Float, default=0)
    risk_score: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    content = relationship("RedditContent")
    __table_args__ = (UniqueConstraint("product_id", "reddit_content_id"),)


class PolicyDecision(Base):
    __tablename__ = "policy_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    policy_version: Mapped[str] = mapped_column(String(30), default="v1")
    decision: Mapped[str] = mapped_column(String(40))
    reply_mode: Mapped[str] = mapped_column(String(60), default="NONE")
    link_policy: Mapped[str] = mapped_column(String(60), default="NO_LINK_UNLESS_REQUESTED")
    required_disclosure: Mapped[bool] = mapped_column(Boolean, default=True)
    max_followups: Mapped[int] = mapped_column(Integer, default=4)
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    input_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    candidate = relationship("Candidate")


class ReplyPlan(Base):
    __tablename__ = "reply_plans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    plan_json: Mapped[dict] = mapped_column(JSON, default=dict)
    claim_ids: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(40), default="PLANNED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GeneratedReply(Base):
    __tablename__ = "generated_replies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    policy_decision_id: Mapped[str | None] = mapped_column(ForeignKey("policy_decisions.id"))
    reply_plan_id: Mapped[str | None] = mapped_column(ForeignKey("reply_plans.id"))
    body: Mapped[str] = mapped_column(Text)
    body_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(40), default="QUALITY_PASSED")
    quality_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PublishedReply(Base):
    __tablename__ = "published_replies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    reddit_account_id: Mapped[str | None] = mapped_column(ForeignKey("reddit_accounts.id"))
    reddit_comment_id: Mapped[str] = mapped_column(String(80), unique=True)
    parent_reddit_fullname: Mapped[str] = mapped_column(String(40))
    body: Mapped[str] = mapped_column(Text)
    body_hash: Mapped[str] = mapped_column(String(64))
    product_brain_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("product_brain_versions.id")
    )
    policy_decision_id: Mapped[str | None] = mapped_column(ForeignKey("policy_decisions.id"))
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(40), default="SHADOW_RECORDED")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    published_reply_id: Mapped[str | None] = mapped_column(ForeignKey("published_replies.id"))
    state: Mapped[str] = mapped_column(String(40), default="POSTED")
    engagement_score: Mapped[float] = mapped_column(Float, default=0)
    conversion_state: Mapped[str] = mapped_column(String(40), default="NONE")
    followup_count: Mapped[int] = mapped_column(Integer, default=0)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    next_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_reason: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    published_reply = relationship("PublishedReply")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    reddit_comment_id: Mapped[str] = mapped_column(String(80), unique=True)
    author_type: Mapped[str] = mapped_column(String(30))
    body: Mapped[str] = mapped_column(Text)
    intent_label: Mapped[str | None] = mapped_column(String(60))
    created_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TrackingLink(Base):
    __tablename__ = "tracking_links"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"))
    short_code: Mapped[str] = mapped_column(String(40), unique=True)
    destination_url: Mapped[str] = mapped_column(String(2048))
    utm_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TrackingEvent(Base):
    __tablename__ = "tracking_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str | None] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    tracking_link_id: Mapped[str | None] = mapped_column(ForeignKey("tracking_links.id"))
    anonymous_id: Mapped[str | None] = mapped_column(String(120))
    user_id: Mapped[str | None] = mapped_column(String(120))
    event_name: Mapped[str] = mapped_column(String(80))
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RiskEvent(Base):
    __tablename__ = "risk_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    product_id: Mapped[str | None] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    reddit_account_id: Mapped[str | None] = mapped_column(ForeignKey("reddit_accounts.id"))
    subreddit_id: Mapped[str | None] = mapped_column(ForeignKey("subreddits.id"))
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"))
    event_type: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(30), default="INFO")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    action_taken: Mapped[str] = mapped_column(String(120), default="AUDIT_ONLY")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ModelRun(Base):
    __tablename__ = "model_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    run_type: Mapped[str] = mapped_column(String(60))
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(36))
    provider: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(30))
    input_hash: Mapped[str] = mapped_column(String(64))
    input_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    output_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="SUCCEEDED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
