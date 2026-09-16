import pytest

from app.config import Settings
from app.evaluation.service import _load_metrics, _LoadMeasurement
from app.reranking import RerankerError, RerankerProvider


@pytest.mark.asyncio
async def test_none_reranker_reports_a_controlled_fallback() -> None:
    provider = RerankerProvider(Settings(reranker_provider="none"))

    with pytest.raises(RerankerError, match="reranker_disabled"):
        await provider.rank("coffee", [{"id": "gc_1", "content": "coffee gift"}], "minilm_l6")


def test_local_reranker_presets_are_allowlisted() -> None:
    provider = RerankerProvider(Settings())

    assert [preset.id for preset in provider.presets] == ["minilm_l6", "tinybert_l2"]
    assert provider.preset_for("tinybert_l2").model == "cross-encoder/ms-marco-TinyBERT-L-2-v2"
    with pytest.raises(RerankerError, match="reranker_unknown"):
        provider.preset_for("not-a-model")


def test_load_metrics_include_errors_fallbacks_and_tail_latency() -> None:
    metrics = _load_metrics(
        [
            _LoadMeasurement(latency_ms=10, error=False, fallback=False),
            _LoadMeasurement(latency_ms=20, error=False, fallback=True),
            _LoadMeasurement(latency_ms=100, error=True, fallback=False),
        ]
    )

    assert metrics.request_count == 3
    assert metrics.error_count == 1
    assert metrics.fallback_count == 1
    assert metrics.latency_p50_ms == 20
    assert metrics.latency_p95_ms == 100
