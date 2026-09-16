ROUTES = [
    {
        "name": "product_search",
        "distance_threshold": 0.58,
        "references": [
            "show me a gift card",
            "I need a present for a teacher",
            "Best Buy",
            "find a coffee gift",
        ],
    },
    {
        "name": "balance_check",
        "distance_threshold": 0.42,
        "references": [
            "check my balance",
            "how much is left on my card",
            "what is my gift card balance",
        ],
    },
    {
        "name": "card_activation",
        "distance_threshold": 0.42,
        "references": [
            "activate my card",
            "my new card needs activation",
            "activate this gift card",
        ],
    },
    {
        "name": "order_status",
        "distance_threshold": 0.42,
        "references": [
            "where is my order",
            "track my gift card",
            "check my order status",
        ],
    },
    {
        "name": "customer_support",
        "distance_threshold": 0.46,
        "references": [
            "I need help",
            "my card is not working",
            "contact customer support",
        ],
    },
]


ACTION_CARDS = {
    "balance_check": {
        "title": "Check a gift card balance",
        "description": "Continue to the simulated balance lookup journey.",
        "destination_label": "Balance lookup",
    },
    "card_activation": {
        "title": "Activate a gift card",
        "description": "Continue to the simulated card activation journey.",
        "destination_label": "Card activation",
    },
    "order_status": {
        "title": "Track a gift card order",
        "description": "Continue to the simulated order-status journey.",
        "destination_label": "Order status",
    },
    "customer_support": {
        "title": "Get gift card support",
        "description": "Continue to the simulated customer-support journey.",
        "destination_label": "Customer support",
    },
}


DETERMINISTIC_ACTIONS = {
    "check my balance": "balance_check",
    "how much is left on my card": "balance_check",
    "what is my gift card balance": "balance_check",
    "activate my card": "card_activation",
    "my new card needs activation": "card_activation",
    "activate this card": "card_activation",
    "where is my order": "order_status",
    "track my gift card": "order_status",
    "check my order status": "order_status",
    "i need help": "customer_support",
    "my card is not working": "customer_support",
    "contact customer support": "customer_support",
}
