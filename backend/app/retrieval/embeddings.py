import hashlib
import json

import numpy as np
from redis.asyncio import Redis
from redisvl.utils.vectorize import HFTextVectorizer

from app.config import Settings
from app.retrieval.catalog import normalize_text_query


class EmbeddingService:
    """RedisVL local embeddings with a Redis-backed normalized-query cache."""

    def __init__(self, settings: Settings, redis_client: Redis) -> None:
        self._settings = settings
        self._redis = redis_client
        self._vectorizer: HFTextVectorizer | None = None

    def _get_vectorizer(self) -> HFTextVectorizer:
        if self._vectorizer is None:
            self._vectorizer = HFTextVectorizer(
                model=self._settings.embedding_model,
            )
        return self._vectorizer

    async def embed_catalog(self, records: list[dict[str, object]]) -> list[dict[str, object]]:
        vectorizer = self._get_vectorizer()
        embeddings = await vectorizer.aembed_many(
            contents=[str(record["embedding_text"]) for record in records],
            batch_size=32,
        )
        for record, embedding in zip(records, embeddings, strict=True):
            if len(embedding) != self._settings.embedding_dims:
                raise ValueError(
                    f"Embedding dimension {len(embedding)} does not match "
                    f"configured dimension {self._settings.embedding_dims}"
                )
            record["embedding"] = np.asarray(embedding, dtype=np.float32).tobytes()
        return records

    async def embed_query(self, query: str) -> list[float]:
        normalized = normalize_text_query(query)
        cache_key = self._cache_key(normalized)
        cached = await self._redis.get(cache_key)
        if cached is not None:
            return [float(value) for value in json.loads(cached)]

        vector = await self._get_vectorizer().aembed(content=normalized)
        values = [float(value) for value in vector]
        if len(values) != self._settings.embedding_dims:
            raise ValueError(
                f"Embedding dimension {len(values)} does not match "
                f"configured dimension {self._settings.embedding_dims}"
            )
        await self._redis.set(
            cache_key,
            json.dumps(values, separators=(",", ":")),
            ex=self._settings.embedding_cache_ttl_seconds,
        )
        return values

    def _cache_key(self, normalized_query: str) -> str:
        digest = hashlib.sha256(
            f"{self._settings.embedding_model}:{normalized_query}".encode()
        ).hexdigest()
        return f"demo:cache:embedding:{digest}"
