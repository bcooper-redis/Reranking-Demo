import json

import pytest

from app.models.search import ClickEventRequest, ComparisonResponse, IntentDecision, SearchResponse
from app.telemetry import TelemetryService


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def set(self, key: str, value: str) -> None:
        self.values[key] = value


@pytest.mark.asyncio
async def test_telemetry_records_synthetic_impressions_and_clicks() -> None:
    redis = FakeRedis()
    service = TelemetryService(redis)  # type: ignore[arg-type]
    response = SearchResponse(
        request_id="request-1",
        query="synthetic demo query",
        mode="hybrid",
        results=[],
        timings_ms={},
        intent=IntentDecision(
            name="product_search",
            confidence=0.9,
            source="redisvl_semantic_router",
        ),
    )

    await service.record_impression(response, tenant_id="general", profile_id="anonymous")
    await service.record_impression(
        ComparisonResponse(
            request_id="request-2",
            query="synthetic comparison query",
            mode="compare",
            comparisons={
                "baseline": response.model_copy(update={"mode": "baseline"}),
                "hybrid": response,
                "reranked": response.model_copy(update={"mode": "reranked"}),
            },
        ),
        tenant_id="general",
        profile_id="anonymous",
    )
    event_id = await service.record_click(
        ClickEventRequest(
            request_id="request-1",
            result_id="gc_demo",
            mode="hybrid",
            tenant_id="general",
        )
    )

    events = [json.loads(value) for value in redis.values.values()]
    assert {event["type"] for event in events} == {"impression", "click"}
    assert any(event["id"] == event_id for event in events)
    snapshot = service.snapshot()
    assert snapshot.click_count == 1
    assert snapshot.route_distribution == {"product_search": 2}
