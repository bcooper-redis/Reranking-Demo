from dataclasses import dataclass


@dataclass(frozen=True)
class GoldenQuery:
    query: str
    expected_intent: str
    relevant_ids: tuple[str, ...] = ()
    exact_brand: bool = False


GOLDEN_QUERIES = (
    GoldenQuery("Best Buy", "product_search", ("gc_best_buy",), exact_brand=True),
    GoldenQuery("Target", "product_search", ("gc_target",), exact_brand=True),
    GoldenQuery(
        "coffee gift for my child's teacher",
        "product_search",
        ("gc_starbucks", "gc_krispy_kreme"),
    ),
    GoldenQuery(
        "a thoughtful thank you for an educator",
        "product_search",
        ("gc_starbucks", "gc_krispy_kreme", "gc_office_depot", "gc_staples"),
    ),
    GoldenQuery("check my balance", "balance_check"),
    GoldenQuery("activate my card", "card_activation"),
    GoldenQuery("where is my order", "order_status"),
    GoldenQuery("my card is not working", "customer_support"),
)
