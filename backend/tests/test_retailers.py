from app.config import Settings
from app.retailers import RETAILERS, get_retailer


def test_bhn_retailer_preserves_the_existing_demo_contract() -> None:
    retailer = get_retailer("bhn")

    assert retailer.organization_name == "Blackhawk Networks"
    assert retailer.experience_name == "GiftFind"
    assert retailer.redis.catalog_document_prefix == "demo:bhn:giftcard"
    assert retailer.redis.catalog_index_alias == "demo:bhn:giftcards"
    assert retailer.redis.router_name == "demo:bhn:routes"
    assert retailer.redis.key("tenant", "general") == "demo:bhn:tenant:general"
    assert retailer.legacy_namespaces[0].catalog_index_alias == "demo:giftcards"


def test_settings_resolves_the_configured_retailer() -> None:
    assert Settings().retailer.id == "bhn"


def test_retailer_registry_is_available_to_the_public_demo_config() -> None:
    assert list(RETAILERS) == ["bhn"]
