from app.evaluation.service import _Measurement, _metrics


def test_evaluation_metrics_cover_relevance_route_and_latency() -> None:
    metrics = _metrics(
        [
            _Measurement(
                expected_intent="product_search",
                relevant_ids={"best_buy"},
                exact_brand=True,
                intent="product_search",
                result_ids=["best_buy", "other"],
                latency_ms=12.0,
            ),
            _Measurement(
                expected_intent="product_search",
                relevant_ids={"coffee"},
                exact_brand=False,
                intent="product_search",
                result_ids=["other", "coffee"],
                latency_ms=24.0,
            ),
            _Measurement(
                expected_intent="balance_check",
                relevant_ids=set(),
                exact_brand=False,
                intent="balance_check",
                result_ids=[],
                latency_ms=36.0,
            ),
        ]
    )

    assert metrics.exact_brand_hit_at_1 == 1.0
    assert metrics.mrr == 0.75
    assert metrics.ndcg_at_10 == 0.8155
    assert metrics.recall_at_25 == 1.0
    assert metrics.route_accuracy == 1.0
    assert metrics.latency_p50_ms == 24.0
    assert metrics.latency_p95_ms == 36.0
