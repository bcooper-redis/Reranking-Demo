import json
from dataclasses import dataclass

from fastapi import HTTPException, status
from redis.asyncio import Redis

from app.config import Settings
from app.models.search import ProductResult
from app.retailers import RetailerDefinition


@dataclass(frozen=True)
class PolicyContext:
    tenant_id: str
    profile_id: str
    profile: dict[str, object]
    tenant: dict[str, object]
    promotion: dict[str, object] | None


class PolicyService:
    """Loads Redis-backed policy context and applies bounded post-relevance boosts."""

    def __init__(
        self, settings: Settings, redis_client: Redis, retailer: RetailerDefinition | None = None
    ) -> None:
        self._settings = settings
        self._redis = redis_client
        self._retailer = retailer or settings.retailer

    async def load_context(
        self, tenant_id: str, profile_id: str, promotion_id: str | None
    ) -> PolicyContext:
        tenant = await self._read_record("tenant", tenant_id, "tenant")
        profile = await self._read_record("profile", profile_id, "profile")
        promotion = None
        if promotion_id:
            if promotion_id not in tenant.get("promotion_ids", []):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Promotion is not available for this tenant",
                )
            promotion = await self._read_record("promotion", promotion_id, "promotion")
            if tenant_id not in promotion.get("eligible_tenant_ids", []):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Promotion is not eligible for this tenant",
                )
        return PolicyContext(
            tenant_id=tenant_id,
            profile_id=profile_id,
            profile=profile,
            tenant=tenant,
            promotion=promotion,
        )

    def apply(self, results: list[ProductResult], context: PolicyContext) -> list[ProductResult]:
        limits = _as_mapping(context.tenant.get("policy"))
        personalization_limit = _as_float(limits.get("personalization_max_boost"), 0.0)
        promotion_limit = _as_float(limits.get("promotion_max_boost"), 0.0)

        for result in results:
            score = result.score_breakdown
            if score is None:
                continue
            available_budget = self._settings.policy_total_max_boost
            affinity = self._profile_affinity(result, context.profile)
            personalization = min(
                affinity * self._settings.personalization_affinity_weight,
                personalization_limit,
                available_budget,
            )
            available_budget -= personalization
            promotion = min(
                self._promotion_boost(result, context.promotion),
                promotion_limit,
                available_budget,
            )
            available_budget -= promotion
            popularity = min(
                result.popularity_score * self._settings.popularity_tiebreaker_weight,
                available_budget,
            )
            relevance = result.score or 0.0
            final_score = relevance + personalization + promotion + popularity

            score.personalization_boost = round(personalization, 4)
            score.promotion_boost = round(promotion, 4)
            score.popularity_tiebreaker = round(popularity, 4)
            score.final_score = round(final_score, 4)
            result.score = score.final_score
            result.promoted = promotion > 0

        return sorted(
            results,
            key=lambda result: (
                not bool(result.score_breakdown and result.score_breakdown.exact_match),
                not bool(result.score_breakdown and result.score_breakdown.prefix_match),
                -(result.score_breakdown.final_score or 0.0) if result.score_breakdown else 0.0,
                result.id,
            ),
        )

    async def _read_record(self, record_type: str, record_id: str, label: str) -> dict[str, object]:
        value = await self._redis.get(self._retailer.redis.key(record_type, record_id))
        if value is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown {label}: {record_id}",
            )
        return json.loads(value)

    @staticmethod
    def _profile_affinity(result: ProductResult, profile: dict[str, object]) -> float:
        category_affinities = _as_mapping(profile.get("category_affinities"))
        brand_affinities = _as_mapping(profile.get("brand_affinities"))
        category_affinity = max(
            (_as_float(category_affinities.get(category), 0.0) for category in result.categories),
            default=0.0,
        )
        return max(category_affinity, _as_float(brand_affinities.get(result.brand_name), 0.0))

    def _promotion_boost(self, result: ProductResult, promotion: dict[str, object] | None) -> float:
        if promotion is None:
            return 0.0
        promotion_categories = set(_as_string_list(promotion.get("categories")))
        if not promotion_categories.intersection(result.categories):
            return 0.0
        relevance_score = _as_float(promotion.get("relevance_score"), 0.0)
        return relevance_score * self._settings.promotion_relevance_weight


def _as_mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_string_list(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _as_float(value: object, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default
