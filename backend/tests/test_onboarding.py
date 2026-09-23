import pytest
from pydantic import ValidationError

from app.models.onboarding import RetailerImportRequest
from app.retailers.onboarding import build_retailer, retailer_id_for


def test_imported_retailer_builds_an_isolated_catalog_and_theme() -> None:
    payload = RetailerImportRequest.model_validate(
        {
            "organization_name": "New Company.com",
            "experience_name": "New Company Discovery",
            "catalog_label": "products",
            "theme": {
                "accent": "#123456",
                "accent_strong": "#0A2340",
                "accent_soft": "#EAF2F8",
                "canvas": "#F7F9FA",
            },
            "products": [
                {
                    "brand_name": f"Example Product {number}",
                    "description": "A synthetic product for the dynamic demo catalog.",
                    "categories": ["examples"],
                }
                for number in range(1, 361)
            ],
        }
    )

    retailer = build_retailer(payload)

    assert retailer_id_for(payload.organization_name) == "new-company-com"
    assert retailer.redis.catalog_index_alias == "demo:new-company-com:products"
    assert retailer.theme == payload.theme.model_dump()
    assert retailer.demo_prompts == {
        "customer_query": "examples gift for a shopper",
        "exact_product_query": "Example Product 1",
        "preference_query": "a gift for a shopper",
        "preference_profile_id": "catalog_preference",
        "preference_profile_name": "examples Shopper",
        "preference_category": "examples",
    }
    assert retailer.tenants()[0]["policy"] == {
        "personalization_max_boost": 0.09,
        "promotion_max_boost": 0.0,
    }
    assert retailer.profiles()[1] == {
        "id": "catalog_preference",
        "display_name": "examples Shopper",
        "category_affinities": {"examples": 1.0},
    }
    assert {route["name"] for route in retailer.routes} == {
        "product_search",
        "order_status",
    }
    assert retailer.deterministic_actions["where is my order"] == "order_status"
    records = retailer.generate_catalog(360)
    assert len(records) == 360
    assert {record["tenant_ids"] for record in records} == {"general"}


def test_imported_retailer_derives_prompts_from_catalog_signals() -> None:
    payload = RetailerImportRequest.model_validate(
        {
            "organization_name": "Outdoor Shop",
            "experience_name": "Outdoor Shop Search",
            "theme": {
                "accent": "#123456",
                "accent_strong": "#0A2340",
                "accent_soft": "#EAF2F8",
                "canvas": "#F7F9FA",
            },
            "products": [
                {
                    "brand_name": "Trail Runner",
                    "description": "A synthetic trail shoe for weekend outdoor runners.",
                    "categories": ["Footwear", "Trail Running"],
                    "recipient_tags": ["trail runners"],
                }
            ]
            * 360,
        }
    )

    retailer = build_retailer(payload)

    assert retailer.demo_prompts is not None
    assert retailer.demo_prompts["customer_query"] == "trail running gift for trail runners"
    assert retailer.demo_prompts["preference_query"] == "a gift for trail runners"
    assert retailer.demo_prompts["preference_profile_name"] == "Trail Running Shopper"


def test_imported_retailer_uses_explicit_demo_paths_from_the_payload() -> None:
    prefix_target = {
        "brand_name": "Trailblazer Runner",
        "description": "A synthetic running shoe for weekend outdoor runners.",
        "aliases": ["trailblazer shoe"],
        "categories": ["Footwear", "Running"],
        "recipient_tags": ["weekend runners"],
    }
    literal_prefix_match = {
        "brand_name": "Trail Map",
        "description": "A synthetic paper map for planning outdoor routes.",
        "categories": ["Maps", "Trail Running"],
        "recipient_tags": ["outdoor shoppers"],
    }
    payload = RetailerImportRequest.model_validate(
        {
            "organization_name": "Outdoor Shop",
            "experience_name": "Outdoor Shop Search",
            "theme": {
                "accent": "#123456",
                "accent_strong": "#0A2340",
                "accent_soft": "#EAF2F8",
                "canvas": "#F7F9FA",
            },
            "demo_paths": {
                "customer_query": "trail gear for a weekend adventure",
                "exact_product_query": "Trailblazer Runner",
                "preference_query": "a useful gift for an outdoor runner",
                "preference_profile_name": "Trail Running Fan",
                "preference_category": "Trail Running",
                "prefix_query": "trail",
                "prefix_expected_product": "Trailblazer Runner",
            },
            "products": [prefix_target, literal_prefix_match] + [prefix_target] * 358,
        }
    )

    retailer = build_retailer(payload)

    assert retailer.demo_prompts == {
        "customer_query": "trail gear for a weekend adventure",
        "exact_product_query": "Trailblazer Runner",
        "preference_query": "a useful gift for an outdoor runner",
        "preference_profile_id": "catalog_preference",
        "preference_profile_name": "Trail Running Fan",
        "preference_category": "Trail Running",
        "prefix_query": "trail",
        "prefix_expected_product": "Trailblazer Runner",
    }


def test_imported_retailer_rejects_a_preference_category_missing_from_the_catalog() -> None:
    with pytest.raises(ValidationError, match="must exactly match a product category"):
        RetailerImportRequest.model_validate(
            {
                "organization_name": "Outdoor Shop",
                "experience_name": "Outdoor Shop Search",
                "theme": {
                    "accent": "#123456",
                    "accent_strong": "#0A2340",
                    "accent_soft": "#EAF2F8",
                    "canvas": "#F7F9FA",
                },
                "demo_paths": {
                    "customer_query": "trail gear for a weekend adventure",
                    "exact_product_query": "Trail Runner",
                    "preference_query": "a useful gift for an outdoor runner",
                    "preference_profile_name": "Trail Running Fan",
                    "preference_category": "Camping",
                    "prefix_query": "trail",
                    "prefix_expected_product": "Trail Runner",
                },
                "products": [
                    {
                        "brand_name": "Trail Runner",
                        "description": "A synthetic trail shoe for weekend outdoor runners.",
                        "categories": ["Footwear", "Running"],
                    }
                ]
                * 360,
            }
        )


def test_imported_retailer_rejects_a_prefix_story_without_a_distinct_literal_match() -> None:
    with pytest.raises(ValidationError, match="another catalog product with a literal text match"):
        RetailerImportRequest.model_validate(
            {
                "organization_name": "Outdoor Shop",
                "experience_name": "Outdoor Shop Search",
                "theme": {
                    "accent": "#123456",
                    "accent_strong": "#0A2340",
                    "accent_soft": "#EAF2F8",
                    "canvas": "#F7F9FA",
                },
                "demo_paths": {
                    "customer_query": "trail gear for a weekend adventure",
                    "exact_product_query": "Trailblazer Runner",
                    "preference_query": "a useful gift for an outdoor runner",
                    "preference_profile_name": "Trail Running Fan",
                    "preference_category": "Running",
                    "prefix_query": "trail",
                    "prefix_expected_product": "Trailblazer Runner",
                },
                "products": [
                    {
                        "brand_name": "Trailblazer Runner",
                        "description": "A synthetic running shoe for weekend outdoor runners.",
                        "categories": ["Footwear", "Running"],
                    }
                ]
                * 360,
            }
        )


def test_imported_retailer_requires_prefix_story_fields_for_new_catalogs() -> None:
    with pytest.raises(ValidationError, match="must include prefix_query"):
        RetailerImportRequest.model_validate(
            {
                "organization_name": "Outdoor Shop",
                "experience_name": "Outdoor Shop Search",
                "theme": {
                    "accent": "#123456",
                    "accent_strong": "#0A2340",
                    "accent_soft": "#EAF2F8",
                    "canvas": "#F7F9FA",
                },
                "demo_paths": {
                    "customer_query": "running gear for a weekend adventure",
                    "exact_product_query": "Runner Shoe",
                    "preference_query": "a useful gift for a runner",
                    "preference_profile_name": "Running Fan",
                    "preference_category": "Running",
                },
                "products": [
                    {
                        "brand_name": "Runner Shoe",
                        "description": "A synthetic running shoe for weekend outdoor runners.",
                        "categories": ["Footwear", "Running"],
                    }
                ]
                * 360,
            }
        )


def test_imported_retailer_requires_exactly_360_products() -> None:
    with pytest.raises(ValidationError, match="products must contain exactly 360 items"):
        RetailerImportRequest.model_validate(
            {
                "organization_name": "Too Small Company",
                "experience_name": "Too Small Demo",
                "theme": {
                    "accent": "#123456",
                    "accent_strong": "#0A2340",
                    "accent_soft": "#EAF2F8",
                    "canvas": "#F7F9FA",
                },
                "products": [
                    {
                        "brand_name": f"Example Product {number}",
                        "description": "A synthetic product for the validation test.",
                        "categories": ["examples"],
                    }
                    for number in range(1, 360)
                ],
            }
        )
