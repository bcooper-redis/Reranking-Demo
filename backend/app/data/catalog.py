import re
from itertools import cycle

DISCLAIMER = (
    "The catalog includes a curated public GiftCards.com assortment snapshot and "
    "synthetic relevance-lab scenarios. Availability, denominations, and fulfillment "
    "are demo data and are not a live commerce feed."
)

CATEGORY_BLUEPRINTS = [
    (
        "electronics",
        "technology gifts, devices, accessories, and games",
        ["gamer", "tech lover", "student"],
    ),
    (
        "coffee",
        "coffee, cafes, breakfast, and everyday thank-you gifts",
        ["coffee fan", "coworker"],
    ),
    (
        "restaurants",
        "dining, restaurants, celebrations, and shared meals",
        ["food lover", "couple", "coworker"],
    ),
    (
        "grocery",
        "groceries, everyday essentials, and practical family gifts",
        ["parent", "neighbor", "family"],
    ),
    ("gaming", "video games, consoles, and digital entertainment", ["gamer", "teen", "student"]),
    ("travel", "travel, hotels, rides, and weekend getaways", ["traveler", "couple", "graduate"]),
    ("entertainment", "movies, music, streaming, and nights out", ["movie fan", "teen", "friend"]),
    (
        "home improvement",
        "tools, home projects, and housewarming gifts",
        ["homeowner", "parent", "neighbor"],
    ),
    ("beauty", "beauty, wellness, self care, and spa gifts", ["friend", "parent", "graduate"]),
    ("fashion", "style, apparel, and everyday accessories", ["teen", "friend", "graduate"]),
    ("books", "books, learning, and creative hobbies", ["teacher", "student", "reader"]),
    (
        "general purpose",
        "flexible gifting for any occasion and recipient",
        ["anyone", "coworker", "family"],
    ),
]

# A compact, public GiftCards.com assortment snapshot. Keep this curated rather than
# treating the demo as a production catalog feed; live availability changes frequently.
FIXTURES = [
    {
        "id": "gc_visa_virtual",
        "brand_name": "Visa Virtual Account",
        "aliases": ["visa virtual gift card", "visa egift", "prepaid visa"],
        "description": (
            "A flexible virtual prepaid gift for online shopping and everyday occasions."
        ),
        "categories": ["general purpose"],
        "recipient_tags": ["anyone", "graduate", "friend"],
        "min_denomination": 10,
        "max_denomination": 250,
        "delivery_types": ["egift"],
    },
    {
        "id": "gc_mastercard_virtual",
        "brand_name": "Mastercard Virtual Account",
        "aliases": ["mastercard virtual gift card", "mastercard egift", "prepaid mastercard"],
        "description": (
            "A flexible virtual prepaid option for online gifting and everyday purchases."
        ),
        "categories": ["general purpose"],
        "recipient_tags": ["anyone", "graduate", "friend"],
        "min_denomination": 10,
        "max_denomination": 250,
        "delivery_types": ["egift"],
    },
    {
        "id": "gc_giftcards_com",
        "brand_name": "Giftcards.com eGift",
        "aliases": ["giftcards.com gift card", "giftcards com", "multi-brand gift"],
        "description": "A flexible GiftCards.com card for choosing from a broad brand assortment.",
        "categories": ["general purpose"],
        "recipient_tags": ["anyone", "family", "coworker"],
        "min_denomination": 25,
        "max_denomination": 500,
        "delivery_types": ["egift", "physical"],
    },
    {
        "id": "gc_airbnb",
        "brand_name": "Airbnb Gift Card",
        "aliases": ["airbnb", "travel stay", "vacation rental"],
        "description": "Travel stays and experiences for a getaway, honeymoon, or new adventure.",
        "categories": ["travel"],
        "recipient_tags": ["traveler", "couple", "graduate"],
        "min_denomination": 25,
        "max_denomination": 500,
        "delivery_types": ["egift"],
    },
    {
        "id": "gc_best_buy",
        "brand_name": "Best Buy",
        "aliases": ["bestbuy", "best buy electronics"],
        "description": "Electronics, games, appliances, and technology gifts.",
        "categories": ["electronics", "gaming"],
        "recipient_tags": ["tech lover", "gamer", "student"],
    },
    {
        "id": "gc_chipotle",
        "brand_name": "Chipotle eGift",
        "aliases": ["chipotle", "burrito gift", "chipotle mexican grill"],
        "description": "Burritos, tacos, bowls, and salads for a fast, thoughtful meal gift.",
        "categories": ["restaurants"],
        "recipient_tags": ["food lover", "student", "coworker"],
        "min_denomination": 10,
        "max_denomination": 250,
        "delivery_types": ["egift", "physical"],
    },
    {
        "id": "gc_starbucks",
        "brand_name": "Starbucks eGift",
        "aliases": ["starbucks", "coffee shop", "teacher coffee gift"],
        "description": "Coffee, cafe treats, and an easy thank-you gift for a teacher or coworker.",
        "categories": ["coffee", "restaurants"],
        "recipient_tags": ["teacher", "coffee fan", "coworker"],
        "min_denomination": 15,
        "max_denomination": 500,
        "delivery_types": ["egift"],
    },
    {
        "id": "gc_texas_roadhouse",
        "brand_name": "Texas Roadhouse eGift",
        "aliases": ["texas roadhouse", "steakhouse gift", "family dinner"],
        "description": (
            "A family dinner out with steaks, fresh-baked bread, and made-from-scratch sides."
        ),
        "categories": ["restaurants"],
        "recipient_tags": ["family", "food lover", "couple"],
        "min_denomination": 15,
        "max_denomination": 100,
        "delivery_types": ["egift", "physical"],
    },
    {
        "id": "gc_target",
        "brand_name": "Target eGift",
        "aliases": ["target", "target gift card", "everyday essentials"],
        "description": (
            "Home, apparel, small appliances, and everyday essentials in one flexible gift."
        ),
        "categories": ["general purpose", "grocery"],
        "recipient_tags": ["parent", "student", "family"],
    },
    {
        "id": "gc_lowes",
        "brand_name": "Lowe's eGift",
        "aliases": ["lowes", "home project", "home improvement gift"],
        "description": "Tools, supplies, and inspiration for home projects and housewarming plans.",
        "categories": ["home improvement"],
        "recipient_tags": ["homeowner", "parent", "neighbor"],
    },
    {
        "id": "gc_ulta",
        "brand_name": "Ulta Beauty eGift",
        "aliases": ["ulta", "beauty gift", "makeup and salon"],
        "description": (
            "Beauty, skin care, hair care, fragrance, and salon services for a self-care gift."
        ),
        "categories": ["beauty"],
        "recipient_tags": ["friend", "parent", "graduate"],
    },
    {
        "id": "gc_american_eagle",
        "brand_name": "American Eagle eGift",
        "aliases": ["american eagle", "ae gift card", "jeans gift"],
        "description": "Jeans, apparel, and everyday style for a teen or college student.",
        "categories": ["fashion"],
        "recipient_tags": ["teen", "student", "friend"],
    },
    {
        "id": "gc_saks",
        "brand_name": "Saks Fifth Avenue eGift",
        "aliases": ["saks", "saks fifth avenue", "luxury fashion"],
        "description": (
            "Designer apparel, shoes, handbags, beauty, and accessories for a special occasion."
        ),
        "categories": ["fashion", "beauty"],
        "recipient_tags": ["friend", "graduate", "couple"],
    },
    {
        "id": "gc_lucky_brand",
        "brand_name": "Lucky Brand eGift",
        "aliases": ["lucky brand", "denim gift", "bohemian style"],
        "description": "Vintage-inspired apparel, premium denim, and relaxed everyday style.",
        "categories": ["fashion"],
        "recipient_tags": ["friend", "teen", "graduate"],
    },
    {
        "id": "gc_amc",
        "brand_name": "AMC Theatres eGift",
        "aliases": ["amc theatres", "movie star", "movie tickets"],
        "description": "Movie tickets, theatre concessions, and an entertaining night out for film fans.",
        "categories": ["entertainment"],
        "recipient_tags": ["movie fan", "teen", "friend"],
        "min_denomination": 15,
        "max_denomination": 100,
        "delivery_types": ["egift", "physical"],
    },
    {
        "id": "gc_bloomin",
        "brand_name": "Bloomin' Brands eGift",
        "aliases": ["bloomin brands", "outback gift", "restaurant choice"],
        "description": (
            "A multi-restaurant dining gift spanning steak, seafood, and Italian favorites."
        ),
        "categories": ["restaurants"],
        "recipient_tags": ["food lover", "couple", "coworker"],
    },
    {
        "id": "gc_treat_yourself",
        "brand_name": "One4all Treat Yourself eGift",
        "aliases": ["treat yourself", "one4all", "dining and retail choice"],
        "description": (
            "A multi-brand choice for dining, fashion, and a well-earned personal treat."
        ),
        "categories": ["general purpose", "restaurants", "fashion"],
        "recipient_tags": ["friend", "teacher", "graduate"],
        "min_denomination": 25,
        "max_denomination": 500,
        "delivery_types": ["egift"],
    },
    {
        "id": "gc_krispy_kreme",
        "brand_name": "Krispy Kreme eGift",
        "aliases": ["krispy kreme", "doughnut gift", "coffee and treats"],
        "description": (
            "Coffee and sweet treats for a classroom thank-you or an easy morning surprise."
        ),
        "categories": ["coffee", "restaurants"],
        "recipient_tags": ["teacher", "coffee fan", "classroom"],
    },
    {
        "id": "gc_zaxbys",
        "brand_name": "Zaxby's eGift",
        "aliases": ["zaxbys", "chicken gift", "wings and sandwiches"],
        "description": "Chicken, wings, sandwiches, and salads for a casual meal with friends.",
        "categories": ["restaurants"],
        "recipient_tags": ["teen", "student", "food lover"],
    },
    {
        "id": "gc_minecraft_dungeons",
        "brand_name": "Minecraft Dungeons Ultimate eGift",
        "aliases": ["minecraft dungeons", "xbox game", "gaming gift"],
        "description": (
            "A digital game gift for a player who enjoys adventure, co-op, and Minecraft."
        ),
        "categories": ["gaming", "entertainment"],
        "recipient_tags": ["gamer", "teen", "student"],
        "delivery_types": ["egift"],
    },
    {
        "id": "gc_sephora",
        "brand_name": "Sephora eGift",
        "aliases": ["sephora", "makeup gift", "skin care gift"],
        "description": "Makeup, skin care, hair care, fragrance, and prestige beauty products.",
        "categories": ["beauty"],
        "recipient_tags": ["friend", "graduate", "parent"],
    },
    {
        "id": "gc_office_depot",
        "brand_name": "Office Depot OfficeMax eGift",
        "aliases": ["office depot", "officemax", "school supplies gift"],
        "description": "School supplies, office essentials, technology, and classroom needs.",
        "categories": ["electronics", "books"],
        "recipient_tags": ["teacher", "student", "coworker"],
    },
    {
        "id": "gc_rei",
        "brand_name": "REI Co-op eGift",
        "aliases": ["rei", "outdoor gift", "camping gear"],
        "description": "Outdoor gear, apparel, and adventure essentials for a weekend away.",
        "categories": ["travel", "fashion"],
        "recipient_tags": ["traveler", "graduate", "parent"],
    },
    {
        "id": "gc_staples",
        "brand_name": "Staples eGift",
        "aliases": ["staples", "school supplies", "office gift"],
        "description": "School supplies, office essentials, and practical technology accessories.",
        "categories": ["electronics", "books"],
        "recipient_tags": ["teacher", "student", "coworker"],
    },
    {
        "id": "gc_macys",
        "brand_name": "Macy's eGift",
        "aliases": ["macys", "macy s", "fashion and home gift"],
        "description": (
            "Fashion, home, beauty, and seasonal gifts from a familiar department store."
        ),
        "categories": ["fashion", "home improvement", "beauty"],
        "recipient_tags": ["parent", "friend", "graduate"],
    },
    {
        "id": "gc_wayfair",
        "brand_name": "Wayfair eGift",
        "aliases": ["wayfair", "home decor gift", "furniture gift"],
        "description": "Furniture, home decor, and practical finds for a new home or room refresh.",
        "categories": ["home improvement"],
        "recipient_tags": ["homeowner", "couple", "parent"],
    },
    {
        "id": "gc_southwest",
        "brand_name": "Southwest Airlines eGift",
        "aliases": ["southwest", "airline gift", "flight gift"],
        "description": "A travel gift for flights, family visits, and a well-deserved getaway.",
        "categories": ["travel"],
        "recipient_tags": ["traveler", "graduate", "family"],
    },
    {
        "id": "gc_one4all_ultimate",
        "brand_name": "One4all Ultimate eGift",
        "aliases": ["one4all ultimate", "one4all", "multi-brand choice gift"],
        "description": (
            "A multi-brand choice card across fashion, technology, books, games, and more."
        ),
        "categories": ["general purpose"],
        "recipient_tags": ["anyone", "graduate", "family"],
        "min_denomination": 25,
        "max_denomination": 500,
        "delivery_types": ["egift"],
    },
]

COFFEE_VARIANTS = [
    (
        "Teacher appreciation coffee and cafe treats for a classroom thank-you.",
        ["teacher", "coffee fan", "classroom"],
        ["teacher coffee gift", "classroom thank you"],
    ),
    (
        "Coffeehouse treats for a friend who enjoys a weekend cafe visit.",
        ["friend", "coffee fan", "weekend"],
        ["coffeehouse gift", "weekend cafe"],
    ),
    (
        "A flexible coffee break for a coworker or office appreciation moment.",
        ["coworker", "office", "coffee fan"],
        ["coworker coffee gift", "office coffee break"],
    ),
    (
        "Breakfast and cafe gifting for a parent who enjoys morning coffee.",
        ["parent", "breakfast", "coffee fan"],
        ["breakfast coffee gift", "parent cafe gift"],
    ),
]

COFFEE_TITLE_SERIES = [
    [
        "Classroom Coffee eGift",
        "Faculty Favorite eGift",
        "Teacher Thanks eGift",
        "Morning Meeting eGift",
        "Study Hall Sips eGift",
        "Grading Day Coffee eGift",
        "School Day Start eGift",
    ],
    [
        "Saturday Cafe eGift",
        "Neighborhood Roast eGift",
        "Weekend Pastry eGift",
        "Coffeehouse Catch-Up eGift",
        "Sunday Brunch eGift",
        "Downtown Cafe eGift",
        "Friends' Coffee Run eGift",
    ],
    [
        "Office Break eGift",
        "Team Coffee Run eGift",
        "Desk-Side Coffee eGift",
        "Monday Momentum eGift",
        "Coffee Cart eGift",
        "Project Pause eGift",
        "Afternoon Reset eGift",
    ],
    [
        "Breakfast Table eGift",
        "Morning Kitchen eGift",
        "Early Start eGift",
        "School Drop-Off Coffee eGift",
        "Family Cafe eGift",
        "Sunrise Treats eGift",
        "Weekend Breakfast eGift",
    ],
]

COFFEE_DETAIL_SERIES = [
    "A small cafe balance makes the gesture easy to use.",
    "Designed for an easy treat between everyday commitments.",
    "A flexible pick for a familiar coffee or breakfast stop.",
    "A practical digital gift for a quick coffee and pastry.",
    "A thoughtful option for a shared moment or solo recharge.",
    "A simple way to recognize a helpful person without guessing their order.",
    "A warm thank-you that fits a busy weekday routine.",
]


def _tags(values: list[str]) -> str:
    return "|".join(values)


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


def _brand_alias_prefixes(brand_name: str, aliases: list[str]) -> str:
    prefixes = {
        normalized[:length]
        for value in [brand_name, *aliases]
        if (normalized := _normalized(value))
        for length in range(3, len(normalized) + 1)
    }
    return _tags(sorted(prefixes))


def _record(
    *,
    product_id: str,
    brand_name: str,
    aliases: list[str],
    description: str,
    categories: list[str],
    recipient_tags: list[str],
    ordinal: int,
    min_denomination: int | None = None,
    max_denomination: int | None = None,
    delivery_types: list[str] | None = None,
    tenant_ids: list[str] | None = None,
) -> dict[str, str]:
    delivery_types = delivery_types or (["egift"] if ordinal % 3 == 0 else ["egift", "physical"])
    if tenant_ids is None:
        tenant_ids = ["general"]
        if ordinal % 5 != 0:
            tenant_ids.append("bank_rewards")
        if ordinal % 4 != 0:
            tenant_ids.append("employee_recognition")
    min_denomination = min_denomination or (10 if ordinal % 4 else 25)
    max_denomination = max_denomination or [50, 75, 100, 200, 500][ordinal % 5]
    embedding_text = ". ".join(
        [brand_name, description, " ".join(categories), " ".join(recipient_tags)]
    )
    return {
        "id": product_id,
        "brand_name": brand_name,
        "normalized_brand": _normalized(brand_name),
        "exact_aliases": _tags([_normalized(alias) for alias in aliases]),
        "brand_alias_prefixes": _brand_alias_prefixes(brand_name, aliases),
        "aliases": _tags(aliases),
        "description": description,
        "categories": _tags(categories),
        "occasions": "birthday|holiday|graduation",
        "recipient_tags": _tags(recipient_tags),
        "delivery_types": _tags(delivery_types),
        "country": "US",
        "currency": "USD",
        "min_denomination": str(min_denomination),
        "max_denomination": str(max_denomination),
        "tenant_ids": _tags(tenant_ids),
        "active": "true",
        "popularity_score": f"{0.40 + ((ordinal * 7) % 55) / 100:.2f}",
        "conversion_score": f"{0.35 + ((ordinal * 11) % 60) / 100:.2f}",
        "margin_score": f"{0.25 + ((ordinal * 13) % 50) / 100:.2f}",
        "promotion_ids": "",
        "image_url": "",
        "embedding_text": embedding_text,
    }


def generate_catalog(count: int = 360) -> list[dict[str, str]]:
    """Generate a repeatable catalog from a curated card snapshot and lab scenarios."""
    if count < len(FIXTURES):
        raise ValueError(f"Catalog count must be at least {len(FIXTURES)}")
    records = [
        _record(
            product_id=fixture["id"],
            brand_name=fixture["brand_name"],
            aliases=fixture["aliases"],
            description=fixture["description"],
            categories=fixture["categories"],
            recipient_tags=fixture["recipient_tags"],
            ordinal=index + 1,
            min_denomination=fixture.get("min_denomination"),
            max_denomination=fixture.get("max_denomination"),
            delivery_types=fixture.get("delivery_types"),
        )
        for index, fixture in enumerate(FIXTURES)
    ]
    blueprints = cycle(CATEGORY_BLUEPRINTS)
    for ordinal in range(len(records) + 1, count + 1):
        category, description, recipients = next(blueprints)
        label = category.title().replace(" ", "")
        aliases = [f"{category} gift", f"{category} card"]
        if category == "coffee":
            scenario_index = (ordinal - (len(FIXTURES) + 2)) // len(CATEGORY_BLUEPRINTS)
            variant_index = ((ordinal - 6) // len(CATEGORY_BLUEPRINTS)) % len(COFFEE_VARIANTS)
            variant_description, recipients, variant_aliases = COFFEE_VARIANTS[variant_index]
            series_index = scenario_index % len(COFFEE_DETAIL_SERIES)
            description = " ".join(
                [
                    f"{description.capitalize()}.",
                    variant_description,
                    COFFEE_DETAIL_SERIES[series_index],
                ]
            )
            aliases.extend(variant_aliases)
            brand_name = COFFEE_TITLE_SERIES[variant_index][series_index]
        else:
            brand_name = f"{label} Choice eGift {ordinal:03d}"
        records.append(
            _record(
                product_id=f"gc_{ordinal:03d}",
                brand_name=brand_name,
                aliases=aliases,
                description=description.capitalize(),
                categories=[category],
                recipient_tags=recipients,
                ordinal=ordinal,
            )
        )
    return records


def tenants() -> list[dict[str, object]]:
    return [
        {
            "id": "general",
            "display_name": "General Gift Marketplace",
            "country": "US",
            "currency": "USD",
            "allowed_delivery_types": ["egift", "physical"],
            "promotion_ids": ["promo_teacher_thanks", "promo_dining_discovery"],
            "policy": {"personalization_max_boost": 0.10, "promotion_max_boost": 0.08},
        },
        {
            "id": "bank_rewards",
            "display_name": "Bank Rewards Portal",
            "country": "US",
            "currency": "USD",
            "allowed_delivery_types": ["egift"],
            "promotion_ids": ["promo_dining_discovery"],
            "policy": {"personalization_max_boost": 0.08, "promotion_max_boost": 0.06},
        },
        {
            "id": "employee_recognition",
            "display_name": "Employee Recognition Store",
            "country": "US",
            "currency": "USD",
            "allowed_delivery_types": ["egift", "physical"],
            "promotion_ids": ["promo_teacher_thanks"],
            "policy": {"personalization_max_boost": 0.06, "promotion_max_boost": 0.05},
        },
    ]


def profiles() -> list[dict[str, object]]:
    return [
        {"id": "anonymous", "display_name": "Anonymous", "category_affinities": {}},
        {
            "id": "tech_buyer",
            "display_name": "Tech Buyer",
            "category_affinities": {"electronics": 0.9, "gaming": 0.7},
            "brand_affinities": {"Best Buy": 0.8},
        },
        {
            "id": "coffee_enthusiast",
            "display_name": "Coffee Enthusiast",
            "category_affinities": {"coffee": 0.9},
            "brand_affinities": {"Starbucks eGift": 0.8},
        },
        {
            "id": "parent",
            "display_name": "Parent",
            "category_affinities": {"grocery": 0.7, "general purpose": 0.5},
            "brand_affinities": {"Target eGift": 0.6},
        },
        {
            "id": "food_explorer",
            "display_name": "Food Explorer",
            "category_affinities": {"restaurants": 0.9},
            "brand_affinities": {"Texas Roadhouse eGift": 0.8},
        },
    ]


def promotions() -> list[dict[str, object]]:
    return [
        {
            "id": "promo_teacher_thanks",
            "display_name": "Teacher Thanks: Coffee",
            "eligible_tenant_ids": ["general", "employee_recognition"],
            "categories": ["coffee"],
            "relevance_score": 1.0,
        },
        {
            "id": "promo_dining_discovery",
            "display_name": "Dining Discovery",
            "eligible_tenant_ids": ["general", "bank_rewards"],
            "categories": ["restaurants"],
            "relevance_score": 0.85,
        },
    ]
