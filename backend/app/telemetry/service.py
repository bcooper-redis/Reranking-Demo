import json
import logging
import math
from collections import Counter, deque
from datetime import UTC, datetime
from uuid import uuid4

from redis.asyncio import Redis

from app.models.search import (
    ClickEventRequest,
    ComparisonResponse,
    SearchResponse,
    TelemetrySnapshot,
)

logger = logging.getLogger(__name__)


class TelemetryService:
    """Captures synthetic demo events and maintains in-process presentation metrics."""

    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client
        self._request_count = 0
        self._error_count = 0
        self._fallback_count = 0
        self._click_count = 0
        self._route_distribution: Counter[str] = Counter()
        self._latencies_ms: deque[float] = deque(maxlen=200)

    def record_request(self, *, status_code: int, duration_ms: float) -> None:
        self._request_count += 1
        self._error_count += int(status_code >= 500)
        self._latencies_ms.append(duration_ms)

    async def record_impression(
        self, response: SearchResponse | ComparisonResponse, *, tenant_id: str, profile_id: str
    ) -> None:
        sample = (
            response.comparisons["reranked"]
            if isinstance(response, ComparisonResponse)
            else response
        )
        intent = sample.intent.name if sample.intent else "unknown"
        self._route_distribution[intent] += 1
        self._fallback_count += len(sample.fallbacks)
        event = {
            "id": str(uuid4()),
            "type": "impression",
            "created_at": datetime.now(UTC).isoformat(),
            "request_id": response.request_id,
            "mode": response.mode,
            "tenant_id": tenant_id,
            "profile_id": profile_id,
            "intent": intent,
            "result_ids": [result.id for result in sample.results],
        }
        await self._redis.set(f"demo:search:event:{event['id']}", json.dumps(event))
        logger.info(json.dumps({"event": "search_impression", **event}))

    async def record_click(self, payload: ClickEventRequest) -> str:
        event_id = str(uuid4())
        event = {
            "id": event_id,
            "type": "click",
            "created_at": datetime.now(UTC).isoformat(),
            **payload.model_dump(),
        }
        await self._redis.set(f"demo:search:event:{event_id}", json.dumps(event))
        self._click_count += 1
        logger.info(json.dumps({"event": "result_click", **event}))
        return event_id

    def snapshot(self) -> TelemetrySnapshot:
        return TelemetrySnapshot(
            request_count=self._request_count,
            error_count=self._error_count,
            fallback_count=self._fallback_count,
            route_distribution=dict(self._route_distribution),
            latency_p50_ms=round(_percentile(self._latencies_ms, 0.50), 2),
            latency_p95_ms=round(_percentile(self._latencies_ms, 0.95), 2),
            click_count=self._click_count,
        )


def _percentile(values: deque[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * percentile) - 1)]
