from app.data.catalog import DISCLAIMER, generate_catalog, profiles, promotions, tenants
from app.data.judgments import GOLDEN_QUERIES
from app.data.routes import ACTION_CARDS, DETERMINISTIC_ACTIONS, ROUTES
from app.retailers.models import RedisNamespace, RetailerDefinition

BHN = RetailerDefinition(
    id="bhn",
    organization_name="Blackhawk Networks",
    experience_name="GiftFind",
    experience_subtitle="RedisVL Relevance Lab",
    catalog_label="catalog cards",
    disclaimer=DISCLAIMER,
    redis=RedisNamespace(
        prefix="demo:bhn",
        catalog_key_segment="giftcard",
        catalog_index_alias="demo:bhn:giftcards",
        router_name="demo:bhn:routes",
    ),
    generate_catalog=generate_catalog,
    tenants=tenants,
    profiles=profiles,
    promotions=promotions,
    routes=tuple(ROUTES),
    action_cards=ACTION_CARDS,
    deterministic_actions=DETERMINISTIC_ACTIONS,
    golden_queries=GOLDEN_QUERIES,
    legacy_namespaces=(
        RedisNamespace(
            prefix="demo",
            catalog_key_segment="giftcard",
            catalog_index_alias="demo:giftcards",
            router_name="demo:routes",
        ),
    ),
)
