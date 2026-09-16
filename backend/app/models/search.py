from typing import Literal

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    country: str | None = Field(default=None, min_length=2, max_length=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    delivery_types: list[str] = Field(default_factory=list, max_length=3)
    category: str | None = Field(default=None, max_length=80)
    min_denomination: int | None = Field(default=None, ge=1, le=5_000)
    max_denomination: int | None = Field(default=None, ge=1, le=5_000)


SearchMode = Literal["baseline", "hybrid", "reranked", "compare"]
ResultMode = Literal["baseline", "hybrid", "reranked"]
IntentName = Literal[
    "product_search",
    "balance_check",
    "card_activation",
    "order_status",
    "customer_support",
]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    tenant_id: str = Field(default="general", min_length=1, max_length=80)
    profile_id: str = Field(default="anonymous", min_length=1, max_length=80)
    promotion_id: str | None = Field(default=None, max_length=80)
    mode: SearchMode = "hybrid"
    reranker_id: str = Field(default="minilm_l6", min_length=1, max_length=80)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    limit: int = Field(default=10, ge=1, le=25)
    debug: bool = False


class ScoreBreakdown(BaseModel):
    lexical_score: float | None = None
    lexical_rank: int | None = None
    vector_distance: float | None = None
    vector_rank: int | None = None
    hybrid_score: float | None = None
    reranker_score: float | None = None
    matching_fields: list[str] = Field(default_factory=list)
    personalization_boost: float = 0.0
    promotion_boost: float = 0.0
    popularity_tiebreaker: float = 0.0
    final_score: float | None = None
    exact_match: bool = False
    prefix_match: bool = False


class RedisSearchQuery(BaseModel):
    label: str
    statement: str
    parameters: list[str] = Field(default_factory=list)


class SearchSuggestion(BaseModel):
    id: str
    brand_name: str


class AutocompleteResponse(BaseModel):
    query: str
    suggestions: list[SearchSuggestion] = Field(default_factory=list)
    redis_search_query: RedisSearchQuery | None = None


class IntentDecision(BaseModel):
    name: IntentName
    confidence: float = Field(ge=0, le=1)
    distance: float | None = None
    threshold: float | None = None
    fallback: bool = False
    source: str


class ActionCard(BaseModel):
    intent: IntentName
    title: str
    description: str
    destination_label: str


class ProductResult(BaseModel):
    id: str
    brand_name: str
    description: str
    categories: list[str]
    delivery_types: list[str]
    min_denomination: int
    max_denomination: int
    popularity_score: float = 0.0
    promoted: bool = False
    score: float | None = None
    score_breakdown: ScoreBreakdown | None = None


class SearchResponse(BaseModel):
    request_id: str
    query: str
    mode: ResultMode
    results: list[ProductResult]
    timings_ms: dict[str, float]
    intent: IntentDecision | None = None
    action: ActionCard | None = None
    redis_search_queries: list[RedisSearchQuery] = Field(default_factory=list)
    diagnostics: dict[str, str | int | bool | float] | None = None
    fallbacks: list[str] = Field(default_factory=list)


class ClickEventRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=80)
    result_id: str = Field(min_length=1, max_length=80)
    mode: ResultMode
    tenant_id: str = Field(min_length=1, max_length=80)
    profile_id: str = Field(default="anonymous", min_length=1, max_length=80)


class EventReceipt(BaseModel):
    event_id: str


class EvaluationMetrics(BaseModel):
    query_count: int
    product_query_count: int
    exact_brand_hit_at_1: float
    mrr: float
    ndcg_at_10: float
    recall_at_25: float
    route_accuracy: float
    latency_p50_ms: float
    latency_p95_ms: float


class EvaluationRun(BaseModel):
    id: str
    created_at: str
    configuration: dict[str, str | int | float]
    metrics: dict[ResultMode, EvaluationMetrics]


class EvaluationRequest(BaseModel):
    reranker_id: str = Field(default="minilm_l6", min_length=1, max_length=80)


class LoadTestRequest(EvaluationRequest):
    concurrency: int = Field(default=2, ge=1, le=4)
    rounds: int = Field(default=3, ge=1, le=5)


class LoadTestMetrics(BaseModel):
    request_count: int
    error_count: int
    fallback_count: int
    latency_p50_ms: float
    latency_p95_ms: float


class LoadTestRun(BaseModel):
    id: str
    created_at: str
    configuration: dict[str, str | int | float]
    concurrency: int
    rounds: int
    metrics: dict[ResultMode, LoadTestMetrics]


class TelemetrySnapshot(BaseModel):
    request_count: int
    error_count: int
    fallback_count: int
    route_distribution: dict[str, int]
    latency_p50_ms: float
    latency_p95_ms: float
    click_count: int


class ComparisonResponse(BaseModel):
    request_id: str
    query: str
    mode: Literal["compare"]
    comparisons: dict[Literal["baseline", "hybrid", "reranked"], SearchResponse]


class TenantOption(BaseModel):
    id: str
    display_name: str
    allowed_delivery_types: list[str]
    promotion_ids: list[str] = Field(default_factory=list)


class ProfileOption(BaseModel):
    id: str
    display_name: str


class PromotionOption(BaseModel):
    id: str
    display_name: str
    eligible_tenant_ids: list[str]


class RerankerOption(BaseModel):
    id: str
    display_name: str
    provider: str
    model: str


class PublicConfigResponse(BaseModel):
    tenants: list[TenantOption]
    profiles: list[ProfileOption]
    promotions: list[PromotionOption]
    rerankers: list[RerankerOption]
    modes: list[SearchMode]
    catalog_count: int
    disclaimer: str
