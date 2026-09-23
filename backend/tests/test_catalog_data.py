from app.data.catalog import FIXTURES, generate_catalog
from app.retrieval.catalog import _matching_fields, normalize_text_query, reciprocal_rank_fusion


def test_catalog_is_deterministic_and_has_exact_brand_fixtures() -> None:
    catalog = generate_catalog(360)

    assert len(catalog) == 360
    assert len({record["id"] for record in catalog}) == 360
    assert len(FIXTURES) == 28
    assert {"Best Buy", "Chipotle eGift", "Target eGift"}.issubset(
        {record["brand_name"] for record in catalog}
    )


def test_catalog_indexes_brand_and_alias_prefixes_for_partial_queries() -> None:
    catalog = {record["id"]: record for record in generate_catalog(360)}

    assert "star" in catalog["gc_starbucks"]["brand_alias_prefixes"].split("|")
    assert "best bu" in catalog["gc_best_buy"]["brand_alias_prefixes"].split("|")
    assert "star" not in catalog["gc_138"]["brand_alias_prefixes"].split("|")


def test_short_prefix_walkthrough_has_a_real_literal_and_prefix_contrast() -> None:
    catalog = {record["id"]: record for record in generate_catalog(360)}

    assert "movie star" in catalog["gc_amc"]["aliases"].lower()
    assert "star" not in catalog["gc_starbucks"]["aliases"].lower().split()
    assert "star" not in catalog["gc_starbucks"]["description"].lower().split()


def test_bhn_walkthrough_product_prompts_have_seeded_catalog_evidence() -> None:
    catalog = {record["id"]: record for record in generate_catalog(360)}

    teacher_coffee = catalog["gc_starbucks"]
    assert {"coffee", "teacher"}.issubset(
        set(teacher_coffee["categories"].split("|"))
        | set(teacher_coffee["recipient_tags"].split("|"))
    )

    best_buy = catalog["gc_best_buy"]
    assert best_buy["brand_name"] == "Best Buy"

    gamer_gift = catalog["gc_minecraft_dungeons"]
    assert "gaming" in gamer_gift["categories"].split("|")
    assert "gamer" in gamer_gift["recipient_tags"].split("|")


def test_query_normalization_removes_redis_query_syntax() -> None:
    assert normalize_text_query("H-E-B @ grocery!") == "h e b grocery"


def test_reciprocal_rank_fusion_prefers_higher_rank() -> None:
    assert reciprocal_rank_fusion(1, 60) > reciprocal_rank_fusion(2, 60)


def test_coffee_variants_make_teacher_intent_a_real_ranking_signal() -> None:
    catalog = {record["id"]: record for record in generate_catalog(90)}

    teacher_variant = catalog["gc_054"]
    office_variant = catalog["gc_078"]
    assert "teacher" in teacher_variant["description"].lower()
    assert "teacher" in teacher_variant["recipient_tags"]
    assert "office" in office_variant["description"].lower()
    assert "teacher" not in office_variant["recipient_tags"]


def test_coffee_scenarios_have_distinct_card_titles() -> None:
    coffee_titles = [
        record["brand_name"] for record in generate_catalog(360) if record["categories"] == "coffee"
    ]

    assert len(coffee_titles) == len(set(coffee_titles))


def test_matching_fields_explain_query_evidence() -> None:
    document = {
        "aliases": "teacher coffee gift|classroom thank you",
        "description": "Teacher appreciation coffee and cafe treats for a classroom.",
        "categories": "coffee",
        "occasions": "holiday",
        "recipient_tags": "teacher|coffee fan|classroom",
    }

    assert _matching_fields(document, "coffee gift for my child s teacher") == [
        "alias: coffee, teacher",
        "description: coffee, teacher",
        "category: coffee",
        "recipient: coffee, teacher",
    ]
