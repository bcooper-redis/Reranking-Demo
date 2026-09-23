from collections.abc import Callable
from dataclasses import dataclass

from app.data.judgments import GoldenQuery


@dataclass(frozen=True)
class RedisNamespace:
    """Names used by one demo retailer inside Redis."""

    prefix: str
    catalog_key_segment: str
    catalog_index_alias: str
    router_name: str

    def key(self, *segments: str) -> str:
        return ":".join((self.prefix, *segments))

    def pattern(self, *segments: str) -> str:
        return self.key(*segments)

    @property
    def catalog_document_prefix(self) -> str:
        return self.key(self.catalog_key_segment)


@dataclass(frozen=True)
class RetailerDefinition:
    """Demo-only retailer contract shared by the API, seed command, and Redis services."""

    id: str
    organization_name: str
    experience_name: str
    experience_subtitle: str
    catalog_label: str
    disclaimer: str
    redis: RedisNamespace
    generate_catalog: Callable[[int], list[dict[str, str]]]
    tenants: Callable[[], list[dict[str, object]]]
    profiles: Callable[[], list[dict[str, object]]]
    promotions: Callable[[], list[dict[str, object]]]
    routes: tuple[dict[str, object], ...]
    action_cards: dict[str, dict[str, str]]
    deterministic_actions: dict[str, str]
    golden_queries: tuple[GoldenQuery, ...]
    legacy_namespaces: tuple[RedisNamespace, ...] = ()
    theme: dict[str, str] | None = None
    demo_prompts: dict[str, str] | None = None
