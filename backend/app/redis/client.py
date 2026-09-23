from collections.abc import Awaitable, Callable
from typing import Any

from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from app.config import Settings

RedisFactory = Callable[[], Awaitable[Redis] | Redis]


class RedisClient:
    """Owns the application's shared Redis connection pool."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._pool = ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=settings.redis_max_connections,
            socket_connect_timeout=settings.redis_connect_timeout_seconds,
            socket_timeout=settings.redis_socket_timeout_seconds,
            retry_on_timeout=True,
        )
        self.client: Redis = Redis(connection_pool=self._pool)

    async def ping(self) -> bool:
        return bool(await self.client.ping())

    async def initialize_runtime(self) -> None:
        await self.client.set(self.settings.retailer.redis.key("runtime", "status"), "initialized")

    async def close(self) -> None:
        await self.client.aclose(close_connection_pool=True)

    async def info(self) -> dict[str, Any]:
        return await self.client.info("server")
