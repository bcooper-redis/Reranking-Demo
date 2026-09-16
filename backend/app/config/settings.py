from functools import lru_cache

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration with local-safe defaults."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    redis_url: str = "redis://localhost:6379"
    redis_index_alias: str = "demo:giftcards"
    redis_index_version: str = "v1"
    redis_vector_algorithm: str = "flat"
    embedding_provider: str = "local_hf"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dims: int = Field(default=384, ge=1, le=16_384)
    embedding_cache_ttl_seconds: int = Field(default=3_600, ge=60, le=86_400)
    search_candidate_count: int = Field(default=25, ge=10, le=100)
    search_rrf_k: int = Field(default=60, ge=1, le=200)
    router_name: str = "demo:routes"
    router_timeout_ms: int = Field(default=30_000, ge=1, le=60_000)
    reranker_provider: str = "local_hf"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rerank_top_n: int = Field(default=20, ge=5, le=50)
    rerank_timeout_ms: int = Field(default=250, ge=1, le=60_000)
    personalization_affinity_weight: float = Field(default=0.10, ge=0, le=1)
    promotion_relevance_weight: float = Field(default=0.08, ge=0, le=1)
    popularity_tiebreaker_weight: float = Field(default=0.02, ge=0, le=1)
    policy_total_max_boost: float = Field(default=0.12, ge=0, le=1)
    redis_max_connections: int = Field(default=20, ge=1, le=200)
    redis_connect_timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    redis_socket_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    frontend_origin: HttpUrl = "http://localhost:5173"
    enable_debug: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
