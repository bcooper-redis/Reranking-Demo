import pytest

from app.config import Settings
from app.models.search import IntentDecision, SearchResponse
from app.retrieval.catalog import CatalogService
from app.routing import RoutingService
from app.routing.service import RoutingDecision


class UnavailableRouterService(RoutingService):
    async def _get_router(self):  # type: ignore[no-untyped-def]
        raise RuntimeError("router unavailable")


@pytest.mark.asyncio
async def test_router_failure_uses_deterministic_action_fallback() -> None:
    service = UnavailableRouterService(Settings())

    decision = await service.route("check my balance")

    assert decision.intent.name == "balance_check"
    assert decision.intent.fallback is True
    assert decision.intent.source == "router_unavailable_deterministic_rule"
    assert decision.action is not None


@pytest.mark.asyncio
async def test_router_failure_falls_back_to_product_search_for_unknown_text() -> None:
    service = UnavailableRouterService(Settings())

    decision = await service.route("zxqv blorf lumen")

    assert decision.intent.name == "product_search"
    assert decision.intent.fallback is True
    assert decision.action is None


def test_low_confidence_product_routing_is_not_reported_as_a_search_fallback() -> None:
    response = SearchResponse(
        request_id="request-1",
        query="Yeti Cooler",
        mode="baseline",
        results=[],
        timings_ms={"total_server": 5.0},
    )
    routing = RoutingDecision(
        intent=IntentDecision(
            name="product_search",
            confidence=0.0,
            distance=None,
            threshold=None,
            fallback=True,
            source="router_low_confidence",
        ),
        action=None,
        timing_ms=3.0,
    )

    CatalogService._apply_routing(response, routing)

    assert response.intent == routing.intent
    assert response.fallbacks == []
    assert response.timings_ms["routing"] == 3.0


def test_unavailable_router_still_reports_a_real_search_fallback() -> None:
    response = SearchResponse(
        request_id="request-2",
        query="Yeti Cooler",
        mode="baseline",
        results=[],
        timings_ms={"total_server": 5.0},
    )
    routing = RoutingDecision(
        intent=IntentDecision(
            name="product_search",
            confidence=0.0,
            distance=None,
            threshold=None,
            fallback=True,
            source="router_unavailable",
        ),
        action=None,
        timing_ms=3.0,
    )

    CatalogService._apply_routing(response, routing)

    assert response.fallbacks == ["router_unavailable"]
