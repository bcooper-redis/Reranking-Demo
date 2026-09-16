from redis.asyncio import Redis
from redis.exceptions import ResponseError
from redisvl.index import AsyncSearchIndex

from app.config import Settings


def physical_index_name(settings: Settings) -> str:
    return f"{settings.redis_index_alias}:{settings.redis_index_version}"


def catalog_schema(settings: Settings, *, name: str | None = None) -> dict[str, object]:
    """RedisVL schema for flat catalog Hashes and a future-compatible vector field."""
    return {
        "index": {
            "name": name or physical_index_name(settings),
            "prefix": "demo:giftcard",
            "storage_type": "hash",
        },
        "fields": [
            {"name": "id", "type": "tag"},
            {"name": "brand_name", "type": "text"},
            {"name": "normalized_brand", "type": "tag"},
            {"name": "exact_aliases", "type": "tag", "attrs": {"separator": "|"}},
            {"name": "brand_alias_prefixes", "type": "tag", "attrs": {"separator": "|"}},
            {"name": "aliases", "type": "text"},
            {"name": "description", "type": "text"},
            {"name": "categories", "type": "tag", "attrs": {"separator": "|"}},
            {"name": "occasions", "type": "tag", "attrs": {"separator": "|"}},
            {"name": "recipient_tags", "type": "tag", "attrs": {"separator": "|"}},
            {"name": "delivery_types", "type": "tag", "attrs": {"separator": "|"}},
            {"name": "country", "type": "tag"},
            {"name": "currency", "type": "tag"},
            {"name": "min_denomination", "type": "numeric"},
            {"name": "max_denomination", "type": "numeric"},
            {"name": "tenant_ids", "type": "tag", "attrs": {"separator": "|"}},
            {"name": "active", "type": "tag"},
            {"name": "popularity_score", "type": "numeric"},
            {"name": "conversion_score", "type": "numeric"},
            {"name": "margin_score", "type": "numeric"},
            {"name": "promotion_ids", "type": "tag", "attrs": {"separator": "|"}},
            {"name": "image_url", "type": "text"},
            {"name": "embedding_text", "type": "text"},
            {
                "name": "embedding",
                "type": "vector",
                "attrs": {
                    "dims": settings.embedding_dims,
                    "distance_metric": "cosine",
                    "algorithm": settings.redis_vector_algorithm,
                    "datatype": "float32",
                },
            },
        ],
    }


class CatalogIndex:
    """Owns the RedisVL index lifecycle and its stable Redis Search alias."""

    def __init__(self, settings: Settings, redis_client: Redis) -> None:
        self._settings = settings
        self._redis = redis_client
        self._physical = AsyncSearchIndex.from_dict(
            catalog_schema(settings), redis_client=redis_client
        )
        self._alias = AsyncSearchIndex.from_dict(
            catalog_schema(settings, name=settings.redis_index_alias), redis_client=redis_client
        )

    @property
    def query_index(self) -> AsyncSearchIndex:
        return self._alias

    async def reset(self) -> None:
        try:
            await self._redis.execute_command("FT.ALIASDEL", self._settings.redis_index_alias)
        except ResponseError:
            pass
        if await self._physical.exists():
            await self._physical.delete(drop=True)

    async def ensure_created(self) -> None:
        if not await self._physical.exists():
            await self._physical.create()
        physical_name = physical_index_name(self._settings)
        try:
            await self._redis.execute_command(
                "FT.ALIASUPDATE", self._settings.redis_index_alias, physical_name
            )
        except ResponseError:
            await self._redis.execute_command(
                "FT.ALIASADD", self._settings.redis_index_alias, physical_name
            )

    async def load(self, records: list[dict[str, object]]) -> list[str]:
        return await self._physical.load(records, id_field="id", batch_size=100)

    async def count(self) -> int:
        info = await self._physical.info()
        return int(info.get("num_docs", 0))
