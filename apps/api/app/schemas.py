from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class LLMSettingsUpdate(BaseModel):
    provider: Literal["mock", "openai"] = "openai"
    api_key: str | None = Field(default=None, max_length=500)
    base_url: HttpUrl = "https://api.openai.com/v1"
    model: str = Field(default="", max_length=200)
    enable_thinking: bool = False
    clear_api_key: bool = False

    @model_validator(mode="after")
    def validate_online_provider(self):
        if self.provider == "openai" and not self.model.strip():
            raise ValueError("在线模型需要填写模型名称")
        return self


class LLMSettingsOut(BaseModel):
    provider: str
    base_url: str
    model: str
    enable_thinking: bool
    api_key_configured: bool
    api_key_hint: str | None = None


class LLMTestOut(BaseModel):
    ok: bool
    message: str


class ProductBrainClaim(BaseModel):
    claim: str = Field(min_length=12, max_length=500)
    source_id: str = Field(min_length=1)
    source_quote: str = Field(min_length=8, max_length=700)
    confidence: float = Field(ge=0, le=1)


class ProductBrainQueryGraph(BaseModel):
    direct_terms: list[str] = Field(min_length=3)
    pain_phrases: list[str] = Field(min_length=3)
    intent_patterns: list[str] = Field(min_length=3)
    competitors: list[str]
    use_cases: list[str] = Field(min_length=3)
    negative_terms: list[str]


class ProductBrainData(BaseModel):
    """Strict contract shared by the LLM, retrieval pipeline, and UI."""

    model_config = ConfigDict(extra="ignore")
    product_name: str = Field(min_length=1)
    one_liner: str = Field(min_length=20, max_length=400)
    category: str = Field(min_length=2, max_length=120)
    target_users: list[str] = Field(min_length=1)
    jobs_to_be_done: list[str] = Field(min_length=2)
    pain_points: list[str] = Field(min_length=2)
    use_cases: list[str] = Field(min_length=2)
    competitors: list[str]
    alternatives: list[str] = Field(min_length=1)
    recommend_when: list[str] = Field(min_length=2)
    do_not_recommend_when: list[str] = Field(min_length=1)
    supported_claims: list[ProductBrainClaim] = Field(min_length=1)
    unsupported_or_uncertain_claims: list[str]
    pricing_summary: str = Field(min_length=2)
    disclosure_identity: str = Field(min_length=5)
    query_graph: ProductBrainQueryGraph


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    website_url: HttpUrl | None = None
    github_url: HttpUrl | None = None
    daily_reply_limit: int = Field(default=2, ge=1, le=2)

    @model_validator(mode="after")
    def require_public_source(self):
        if not self.website_url and not self.github_url:
            raise ValueError("请至少填写产品网站或 GitHub 仓库地址")
        return self


class ProductUpdate(BaseModel):
    name: str | None = None
    website_url: HttpUrl | None = None
    github_url: HttpUrl | None = None
    daily_reply_limit: int | None = Field(default=None, ge=1, le=2)
    autopublish_enabled: bool | None = None
    allow_first_reply_link: bool | None = None
    disclosure_template: str | None = None
    is_owned: bool | None = None
    auto_score_threshold: float | None = Field(default=None, ge=0.75, le=0.95)
    auto_risk_threshold: float | None = Field(default=None, ge=0.05, le=0.5)
    search_interval_hours: int | None = Field(default=None, ge=3, le=24)
    min_publish_interval_hours: int | None = Field(default=None, ge=3, le=24)
    keywords_per_run: int | None = Field(default=None, ge=1, le=5)
    details_per_keyword: int | None = Field(default=None, ge=1, le=3)
    target_users: list[str] | None = None
    key_selling_points: list[str] | None = None
    forbidden_claims: list[str] | None = None
    recommend_when: list[str] | None = None
    do_not_recommend_when: list[str] | None = None


class ProductOrderUpdate(BaseModel):
    product_ids: list[str]


class XiaohongshuSearchIn(BaseModel):
    keyword: str = Field(min_length=1, max_length=100)
    detail_limit: int = Field(default=3, ge=1, le=5)


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    website_url: str | None
    github_url: str | None
    status: str
    autopublish_enabled: bool
    daily_reply_limit: int
    allow_first_reply_link: bool
    disclosure_template: str
    is_owned: bool
    auto_score_threshold: float
    auto_risk_threshold: float
    search_interval_hours: int
    min_publish_interval_hours: int
    keywords_per_run: int
    details_per_keyword: int
    automation_status: str
    automation_error: str | None
    automation_failures: int
    last_auto_search_at: datetime | None
    next_auto_search_at: datetime | None
    last_auto_publish_at: datetime | None
    target_users: list
    key_selling_points: list
    forbidden_claims: list
    recommend_when: list
    do_not_recommend_when: list
    sort_order: int
    deleted_at: datetime | None
    purge_after: datetime | None


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    source_type: str
    url: str
    title: str
    content_hash: str


class BrainOut(BaseModel):
    id: str
    version: int
    brain: dict[str, Any]


class OpportunityOut(BaseModel):
    id: str
    status: str
    subreddit: str
    title: str | None
    body: str
    permalink: str
    intent_label: str
    intent_confidence: float
    opportunity_score: float
    risk_score: float
    recall_sources: list
    policy_decision: str | None = None
    generated_reply: str | None = None
    publish_status: str | None = None
    target_type: str | None = None
    author_name: str | None = None
    score_reason: str | None = None
    match_signals: list[str] = Field(default_factory=list)
    publish_error: str | None = None


class RedditAccountCreate(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    status: str = "ACTIVE"
    app_approval_status: str = "DEVELOPMENT_ONLY"


class RedditAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str
    status: str
    app_approval_status: str


class SubredditOut(BaseModel):
    id: str
    name: str
    status: str
    community_score: float
    promotion_tolerance: float
    risk_score: float
    rules: dict[str, Any]


class ProductSubredditPatch(BaseModel):
    status: str | None = None
    promotion_tolerance: float | None = Field(default=None, ge=0, le=1)
    risk_score: float | None = Field(default=None, ge=0, le=1)


class DecisionOut(BaseModel):
    id: str
    decision: str
    reply_mode: str
    link_policy: str
    required_disclosure: bool
    reason_codes: list


class ReplyOut(BaseModel):
    id: str
    body: str
    status: str
    quality: dict[str, Any]


class ConversationOut(BaseModel):
    id: str
    state: str
    conversion_state: str
    followup_count: int
    last_activity_at: Any
    next_check_at: Any | None
    closed_reason: str | None


class AnalyticsOverviewOut(BaseModel):
    scanned: int
    candidates: int
    qualified_opportunities: int
    conversations: int
    waiting_followups: int
    user_questions: int
    link_requests: int
    visits: int
    signups: int
    activations: int
    removals: int
    negative_interactions: int
    risk_level: str


class TrackingEventIn(BaseModel):
    event: str
    product_id: str | None = None
    short_code: str | None = None
    anonymous_id: str | None = None
    user_id: str | None = None
    timestamp: Any | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class FollowupIn(BaseModel):
    body: str
    author_type: str = "user"
