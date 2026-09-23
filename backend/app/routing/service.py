import asyncio
import time
from dataclasses import dataclass

from redis import Redis
from redis.exceptions import ResponseError
from redisvl.extensions.router import SemanticRouter
from redisvl.extensions.router.schema import Route
from redisvl.utils.vectorize import HFTextVectorizer

from app.config import Settings
from app.models.search import ActionCard, IntentDecision
from app.retailers import RetailerDefinition


@dataclass
class RoutingDecision:
    intent: IntentDecision
    action: ActionCard | None
    timing_ms: float


class RoutingService:
    """Owns the RedisVL SemanticRouter and its safe product-search fallback."""

    def __init__(self, settings: Settings, retailer: RetailerDefinition | None = None) -> None:
        self._settings = settings
        self._retailer = retailer or settings.retailer
        self._client: Redis | None = None
        self._router_task: asyncio.Task[SemanticRouter] | None = None

    async def route(self, query: str) -> RoutingDecision:
        started_at = time.perf_counter()
        try:
            router = await self._get_router()
            match = await asyncio.wait_for(
                asyncio.to_thread(router, statement=query),
                timeout=self._settings.router_timeout_ms / 1_000,
            )
        except TimeoutError:
            return self._fallback(query, "router_timeout", started_at)
        except Exception:
            return self._fallback(query, "router_unavailable", started_at)

        if match.name is None:
            return self._fallback(query, "router_low_confidence", started_at)

        route = next(route for route in self._retailer.routes if route["name"] == match.name)
        distance = float(match.distance) if match.distance is not None else None
        intent = IntentDecision(
            name=match.name,
            confidence=round(max(0.0, 1.0 - (distance or 1.0)), 4),
            distance=distance,
            threshold=float(route["distance_threshold"]),
            fallback=False,
            source="redisvl_semantic_router",
        )
        action_data = self._retailer.action_cards.get(match.name)
        action = ActionCard(intent=match.name, **action_data) if action_data else None
        return RoutingDecision(
            intent=intent,
            action=action,
            timing_ms=(time.perf_counter() - started_at) * 1_000,
        )

    async def ensure_initialized(self) -> None:
        await self._get_router()

    async def reset(self) -> None:
        await asyncio.to_thread(self._reset_sync)

    async def close(self) -> None:
        if self._client is not None:
            await asyncio.to_thread(self._client.close)
            self._client = None

    async def _get_router(self) -> SemanticRouter:
        if self._router_task is None:
            self._router_task = asyncio.create_task(asyncio.to_thread(self._build_router))
        try:
            return await asyncio.wait_for(
                asyncio.shield(self._router_task),
                timeout=self._settings.router_timeout_ms / 1_000,
            )
        except TimeoutError as exc:
            raise TimeoutError from exc

    def _build_router(self) -> SemanticRouter:
        self._client = Redis.from_url(
            self._settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=self._settings.redis_connect_timeout_seconds,
            socket_timeout=self._settings.redis_socket_timeout_seconds,
        )
        return SemanticRouter(
            name=self._retailer.redis.router_name,
            routes=[Route(**route) for route in self._retailer.routes],
            vectorizer=HFTextVectorizer(model=self._settings.embedding_model),
            redis_client=self._client,
            overwrite=False,
        )

    def _reset_sync(self) -> None:
        client = self._client or Redis.from_url(self._settings.redis_url, decode_responses=True)
        try:
            client.execute_command("FT.DROPINDEX", self._retailer.redis.router_name, "DD")
        except ResponseError:
            pass
        client.delete(f"{self._retailer.redis.router_name}:route_config")
        if self._client is None:
            client.close()
        self._router_task = None

    def _product_fallback(self, reason: str, started_at: float) -> RoutingDecision:
        return RoutingDecision(
            intent=IntentDecision(
                name="product_search",
                confidence=0.0,
                distance=None,
                threshold=None,
                fallback=True,
                source=reason,
            ),
            action=None,
            timing_ms=(time.perf_counter() - started_at) * 1_000,
        )

    def _fallback(self, query: str, reason: str, started_at: float) -> RoutingDecision:
        route_name = self._retailer.deterministic_actions.get(self._normalize_query(query))
        if route_name is None:
            return self._product_fallback(reason, started_at)

        action_data = self._retailer.action_cards[route_name]
        return RoutingDecision(
            intent=IntentDecision(
                name=route_name,
                confidence=1.0,
                distance=None,
                threshold=None,
                fallback=True,
                source=f"{reason}_deterministic_rule",
            ),
            action=ActionCard(intent=route_name, **action_data),
            timing_ms=(time.perf_counter() - started_at) * 1_000,
        )

    @staticmethod
    def _normalize_query(query: str) -> str:
        return " ".join(
            "".join(
                character if character.isalnum() else " " for character in query.lower()
            ).split()
        )
