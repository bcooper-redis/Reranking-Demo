import pytest

from app.config import Settings
from app.routing import RoutingService


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
