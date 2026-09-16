from app.config import Settings
from app.models.search import ProductResult, ScoreBreakdown
from app.policy import PolicyContext, PolicyService


def _result(
    product_id: str,
    brand_name: str,
    categories: list[str],
    *,
    score: float = 0.5,
    exact_match: bool = False,
) -> ProductResult:
    return ProductResult(
        id=product_id,
        brand_name=brand_name,
        description="Synthetic policy fixture",
        categories=categories,
        delivery_types=["egift"],
        min_denomination=10,
        max_denomination=50,
        score=score,
        score_breakdown=ScoreBreakdown(exact_match=exact_match),
    )


def _context(
    profile: dict[str, object], promotion: dict[str, object] | None = None
) -> PolicyContext:
    return PolicyContext(
        tenant_id="general",
        profile_id=str(profile["id"]),
        profile=profile,
        tenant={
            "policy": {
                "personalization_max_boost": 0.10,
                "promotion_max_boost": 0.08,
            }
        },
        promotion=promotion,
    )


def test_personas_change_an_ambiguous_order() -> None:
    service = PolicyService(Settings(), None)  # type: ignore[arg-type]
    candidates = [
        _result("coffee", "Coffee Card", ["coffee"]),
        _result("tech", "Tech Card", ["electronics"]),
    ]

    coffee = service.apply(
        [candidate.model_copy(deep=True) for candidate in candidates],
        _context({"id": "coffee_enthusiast", "category_affinities": {"coffee": 0.9}}),
    )
    tech = service.apply(
        [candidate.model_copy(deep=True) for candidate in candidates],
        _context({"id": "tech_buyer", "category_affinities": {"electronics": 0.9}}),
    )

    assert coffee[0].id == "coffee"
    assert tech[0].id == "tech"


def test_anonymous_has_no_personalization_boost() -> None:
    service = PolicyService(Settings(), None)  # type: ignore[arg-type]
    result = _result("coffee", "Coffee Card", ["coffee"])

    personalized = service.apply(
        [result.model_copy(deep=True)],
        _context({"id": "coffee_enthusiast", "category_affinities": {"coffee": 0.9}}),
    )[0]
    anonymous = service.apply(
        [result.model_copy(deep=True)],
        _context({"id": "anonymous", "category_affinities": {}}),
    )[0]

    assert personalized.score_breakdown is not None
    assert anonymous.score_breakdown is not None
    assert personalized.score_breakdown.personalization_boost == 0.09
    assert anonymous.score_breakdown.personalization_boost == 0.0


def test_promotion_is_bounded_and_relevant_only() -> None:
    service = PolicyService(Settings(), None)
    promotion = {
        "id": "promo_teacher_thanks",
        "categories": ["coffee"],
        "relevance_score": 1.0,
    }
    coffee = _result("coffee", "Coffee Card", ["coffee"])
    electronics = _result("tech", "Tech Card", ["electronics"])

    ranked = service.apply(
        [coffee, electronics],
        _context({"id": "anonymous", "category_affinities": {}}, promotion),
    )

    promoted = next(result for result in ranked if result.id == "coffee")
    unpromoted = next(result for result in ranked if result.id == "tech")
    assert promoted.promoted is True
    assert promoted.score_breakdown is not None
    assert promoted.score_breakdown.promotion_boost == 0.08
    assert unpromoted.promoted is False
    assert unpromoted.score_breakdown is not None
    assert unpromoted.score_breakdown.promotion_boost == 0.0
    assert {result.id for result in ranked} == {"coffee", "tech"}


def test_exact_brand_remains_first_after_policy_scoring() -> None:
    service = PolicyService(Settings(), None)
    exact = _result("best_buy", "Best Buy", ["electronics"], score=0.1, exact_match=True)
    boosted = _result("coffee", "Coffee Card", ["coffee"], score=0.5)

    ranked = service.apply(
        [exact, boosted],
        _context({"id": "coffee_enthusiast", "category_affinities": {"coffee": 0.9}}),
    )

    assert ranked[0].id == "best_buy"


def test_brand_prefix_remains_first_after_policy_scoring() -> None:
    service = PolicyService(Settings(), None)
    prefix = _result("starbucks", "Starbucks eGift", ["coffee"], score=0.1)
    prefix.score_breakdown.prefix_match = True
    boosted = _result("entertainment", "Entertainment Choice", ["entertainment"], score=0.5)

    ranked = service.apply(
        [boosted, prefix], _context({"id": "anonymous", "category_affinities": {}})
    )

    assert ranked[0].id == "starbucks"
