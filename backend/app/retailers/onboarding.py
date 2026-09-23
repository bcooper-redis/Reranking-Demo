"""Build and persist user-supplied demo retailers for the internal demo foundry."""

import re
from collections.abc import Iterable

from redis.asyncio import Redis

from app.data.catalog import _record
from app.models.onboarding import RetailerPayload, StoredRetailerPayload
from app.retailers.models import RedisNamespace, RetailerDefinition

CONFIGURATION_PREFIX = "demo:retailer:configuration"


def retailer_id_for(organization_name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", organization_name.lower()).strip("-")
    return normalized[:48] or "custom-retailer"


def _recipient_phrase(value: str) -> str:
    """Make imported persona tags read naturally in generated shopper prompts."""
    normalized = value.strip()
    return normalized if normalized.endswith("s") else f"a {normalized}"


def _demo_prompts(payload: RetailerPayload) -> dict[str, str]:
    if payload.demo_paths:
        prompts = {
            "customer_query": payload.demo_paths.customer_query,
            "exact_product_query": payload.demo_paths.exact_product_query,
            "preference_query": payload.demo_paths.preference_query,
            "preference_profile_id": "catalog_preference",
            "preference_profile_name": payload.demo_paths.preference_profile_name,
            "preference_category": payload.demo_paths.preference_category,
        }
        if (
            payload.demo_paths.prefix_query
            and payload.demo_paths.prefix_expected_product
        ):
            prompts["prefix_query"] = payload.demo_paths.prefix_query
            prompts["prefix_expected_product"] = payload.demo_paths.prefix_expected_product
        return prompts

    # Keep existing saved Foundry payloads usable while new payloads provide these explicitly.
    featured_product = payload.products[0]
    category = featured_product.categories[-1]
    recipient = featured_product.recipient_tags[0]
    recipient_phrase = _recipient_phrase(recipient)
    return {
        "customer_query": f"{category.lower()} gift for {recipient_phrase}",
        "exact_product_query": featured_product.brand_name,
        "preference_query": f"a gift for {recipient_phrase}",
        "preference_profile_id": "catalog_preference",
        "preference_profile_name": f"{category} Shopper",
        "preference_category": category,
    }


def build_retailer(payload: RetailerPayload) -> RetailerDefinition:
    retailer_id = retailer_id_for(payload.organization_name)
    prompts = _demo_prompts(payload)
    records = [
        _record(
            product_id=f"product_{ordinal:03d}",
            brand_name=product.brand_name,
            aliases=list(dict.fromkeys([product.brand_name, *product.aliases])),
            description=product.description,
            categories=product.categories,
            recipient_tags=product.recipient_tags,
            ordinal=ordinal,
            min_denomination=product.min_price,
            max_denomination=product.max_price,
            delivery_types=product.delivery_types,
            tenant_ids=["general"],
        )
        for ordinal, product in enumerate(payload.products, start=1)
    ]
    return RetailerDefinition(
        id=retailer_id,
        organization_name=payload.organization_name,
        experience_name=payload.experience_name,
        experience_subtitle="RedisVL Product Discovery Lab",
        catalog_label=payload.catalog_label,
        disclaimer=(
            f"The {payload.organization_name} experience uses a synthetic catalog supplied "
            "through the internal demo foundry. It is not a live commerce feed."
        ),
        redis=RedisNamespace(
            prefix=f"demo:{retailer_id}",
            catalog_key_segment="product",
            catalog_index_alias=f"demo:{retailer_id}:products",
            router_name=f"demo:{retailer_id}:routes",
        ),
        generate_catalog=lambda _count: records,
        tenants=lambda: [
            {
                "id": "general",
                "display_name": "General Storefront",
                "country": "US",
                "currency": "USD",
                "allowed_delivery_types": ["shipping", "pickup", "digital"],
                "promotion_ids": [],
                "policy": {"personalization_max_boost": 0.09, "promotion_max_boost": 0.0},
            }
        ],
        profiles=lambda: [
            {"id": "anonymous", "display_name": "Anonymous", "category_affinities": {}},
            {
                "id": prompts["preference_profile_id"],
                "display_name": prompts["preference_profile_name"],
                "category_affinities": {prompts["preference_category"]: 1.0},
            },
        ],
        promotions=lambda: [],
        routes=(
            {
                "name": "product_search",
                "distance_threshold": 0.58,
                "references": [
                    product.brand_name for product in payload.products[:4]
                ]
                + ["find products", "show me popular items"],
            },
            {
                "name": "order_status",
                "distance_threshold": 0.42,
                "references": [
                    "where is my order",
                    "track my order",
                    "check my order status",
                ],
            },
        ),
        action_cards={
            "order_status": {
                "title": "Track an order",
                "description": (
                    f"Continue to the simulated {payload.organization_name} order-status journey."
                ),
                "destination_label": "Order status",
            }
        },
        deterministic_actions={
            "where is my order": "order_status",
            "track my order": "order_status",
            "check my order status": "order_status",
        },
        golden_queries=(),
        theme=payload.theme.model_dump(),
        demo_prompts=prompts,
    )


async def save_payload(redis: Redis, payload: RetailerPayload) -> None:
    retailer_id = retailer_id_for(payload.organization_name)
    await redis.set(f"{CONFIGURATION_PREFIX}:{retailer_id}", payload.model_dump_json())


async def load_retailers(redis: Redis) -> dict[str, RetailerDefinition]:
    retailers: dict[str, RetailerDefinition] = {}
    async for key in redis.scan_iter(match=f"{CONFIGURATION_PREFIX}:*"):
        value = await redis.get(key)
        if value:
            payload = StoredRetailerPayload.model_validate_json(value)
            retailer = build_retailer(payload)
            retailers[retailer.id] = retailer
    return retailers


def is_builtin(retailer_id: str, builtin_retailers: Iterable[str]) -> bool:
    return retailer_id in set(builtin_retailers)
