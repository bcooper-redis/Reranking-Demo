import asyncio
import math
import time
from collections import defaultdict
from datetime import UTC, datetime
from uuid import uuid4

from redis.asyncio import Redis

from app.config import Settings
from app.data import GOLDEN_QUERIES
from app.data.judgments import GoldenQuery
from app.models.search import (
    EvaluationMetrics,
    EvaluationRun,
    LoadTestMetrics,
    LoadTestRun,
    SearchRequest,
    SearchResponse,
)
from app.retrieval import CatalogService

EVALUATION_MODES = ("baseline", "hybrid", "reranked")


class EvaluationService:
    """Runs version-controlled golden queries and persists reproducible scorecards."""

    def __init__(self, settings: Settings, redis_client: Redis, catalog: CatalogService) -> None:
        self._settings = settings
        self._redis = redis_client
        self._catalog = catalog

    async def run(self, reranker_id: str = "minilm_l6") -> EvaluationRun:
        reranker = self._catalog.reranker_preset(reranker_id)
        measurements: dict[str, list[_Measurement]] = defaultdict(list)
        for mode in EVALUATION_MODES:
            for golden in GOLDEN_QUERIES:
                started_at = time.perf_counter()
                response = await self._catalog.search(
                    SearchRequest(
                        query=golden.query,
                        mode=mode,
                        reranker_id=reranker_id,
                        debug=True,
                    )
                )
                elapsed_ms = (time.perf_counter() - started_at) * 1_000
                if not isinstance(response, SearchResponse):
                    raise RuntimeError("Evaluation requests must return a single-mode response")
                measurements[mode].append(
                    _Measurement(
                        expected_intent=golden.expected_intent,
                        relevant_ids=set(golden.relevant_ids),
                        exact_brand=golden.exact_brand,
                        intent=response.intent.name if response.intent else "unknown",
                        result_ids=[result.id for result in response.results],
                        latency_ms=elapsed_ms,
                    )
                )

        evaluation_id = str(uuid4())
        run = EvaluationRun(
            id=evaluation_id,
            created_at=datetime.now(UTC).isoformat(),
            configuration={
                "index_alias": self._settings.redis_index_alias,
                "index_version": self._settings.redis_index_version,
                "embedding_model": self._settings.embedding_model,
                "reranker_id": reranker.id,
                "reranker_provider": reranker.provider,
                "reranker_model": reranker.model,
                "candidate_count": self._settings.search_candidate_count,
                "rerank_top_n": self._settings.rerank_top_n,
            },
            metrics={mode: _metrics(items) for mode, items in measurements.items()},
        )
        await self._redis.set(
            f"demo:evaluation:{evaluation_id}",
            run.model_dump_json(),
        )
        return run

    async def get(self, evaluation_id: str) -> EvaluationRun | None:
        value = await self._redis.get(f"demo:evaluation:{evaluation_id}")
        return EvaluationRun.model_validate_json(value) if value else None

    async def run_load(
        self, reranker_id: str = "minilm_l6", concurrency: int = 2, rounds: int = 3
    ) -> LoadTestRun:
        reranker = self._catalog.reranker_preset(reranker_id)
        product_queries = [golden for golden in GOLDEN_QUERIES if golden.relevant_ids]
        metrics: dict[str, LoadTestMetrics] = {}
        for mode in EVALUATION_MODES:
            measurements = await self._run_concurrent_product_queries(
                product_queries, mode, reranker_id, concurrency, rounds
            )
            metrics[mode] = _load_metrics(measurements)

        load_id = str(uuid4())
        run = LoadTestRun(
            id=load_id,
            created_at=datetime.now(UTC).isoformat(),
            configuration={
                "index_alias": self._settings.redis_index_alias,
                "index_version": self._settings.redis_index_version,
                "embedding_model": self._settings.embedding_model,
                "reranker_id": reranker.id,
                "reranker_provider": reranker.provider,
                "reranker_model": reranker.model,
                "candidate_count": self._settings.search_candidate_count,
                "rerank_top_n": self._settings.rerank_top_n,
            },
            concurrency=concurrency,
            rounds=rounds,
            metrics=metrics,
        )
        await self._redis.set(f"demo:evaluation-load:{load_id}", run.model_dump_json())
        return run

    async def _run_concurrent_product_queries(
        self,
        product_queries: list[GoldenQuery],
        mode: str,
        reranker_id: str,
        concurrency: int,
        rounds: int,
    ) -> list["_LoadMeasurement"]:
        semaphore = asyncio.Semaphore(concurrency)

        async def run_query(golden: GoldenQuery) -> _LoadMeasurement:
            async with semaphore:
                started_at = time.perf_counter()
                try:
                    response = await self._catalog.search(
                        SearchRequest(
                            query=golden.query,
                            mode=mode,
                            reranker_id=reranker_id,
                            debug=True,
                        )
                    )
                    if not isinstance(response, SearchResponse):
                        raise RuntimeError("Load tests must return a single-mode response")
                    return _LoadMeasurement(
                        latency_ms=(time.perf_counter() - started_at) * 1_000,
                        error=False,
                        fallback=bool(response.fallbacks),
                    )
                except Exception:
                    return _LoadMeasurement(
                        latency_ms=(time.perf_counter() - started_at) * 1_000,
                        error=True,
                        fallback=False,
                    )

        return list(
            await asyncio.gather(
                *(run_query(golden) for _ in range(rounds) for golden in product_queries)
            )
        )


class _Measurement:
    def __init__(
        self,
        *,
        expected_intent: str,
        relevant_ids: set[str],
        exact_brand: bool,
        intent: str,
        result_ids: list[str],
        latency_ms: float,
    ) -> None:
        self.expected_intent = expected_intent
        self.relevant_ids = relevant_ids
        self.exact_brand = exact_brand
        self.intent = intent
        self.result_ids = result_ids
        self.latency_ms = latency_ms


class _LoadMeasurement:
    def __init__(self, *, latency_ms: float, error: bool, fallback: bool) -> None:
        self.latency_ms = latency_ms
        self.error = error
        self.fallback = fallback


def _metrics(measurements: list[_Measurement]) -> EvaluationMetrics:
    product = [item for item in measurements if item.relevant_ids]
    exact = [item for item in product if item.exact_brand]
    return EvaluationMetrics(
        query_count=len(measurements),
        product_query_count=len(product),
        exact_brand_hit_at_1=_mean(
            [float(item.result_ids[:1] == [next(iter(item.relevant_ids))]) for item in exact]
        ),
        mrr=_mean([_reciprocal_rank(item.result_ids, item.relevant_ids) for item in product]),
        ndcg_at_10=_mean([_ndcg_at_10(item.result_ids, item.relevant_ids) for item in product]),
        recall_at_25=_mean([_recall_at_25(item.result_ids, item.relevant_ids) for item in product]),
        route_accuracy=_mean([float(item.intent == item.expected_intent) for item in measurements]),
        latency_p50_ms=round(_percentile([item.latency_ms for item in measurements], 0.50), 2),
        latency_p95_ms=round(_percentile([item.latency_ms for item in measurements], 0.95), 2),
    )


def _load_metrics(measurements: list[_LoadMeasurement]) -> LoadTestMetrics:
    latencies = [measurement.latency_ms for measurement in measurements]
    return LoadTestMetrics(
        request_count=len(measurements),
        error_count=sum(measurement.error for measurement in measurements),
        fallback_count=sum(measurement.fallback for measurement in measurements),
        latency_p50_ms=round(_percentile(latencies, 0.50), 2),
        latency_p95_ms=round(_percentile(latencies, 0.95), 2),
    )


def _reciprocal_rank(result_ids: list[str], relevant_ids: set[str]) -> float:
    for rank, result_id in enumerate(result_ids, start=1):
        if result_id in relevant_ids:
            return 1 / rank
    return 0.0


def _ndcg_at_10(result_ids: list[str], relevant_ids: set[str]) -> float:
    dcg = sum(
        1 / math.log2(rank + 1)
        for rank, result_id in enumerate(result_ids[:10], start=1)
        if result_id in relevant_ids
    )
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, min(len(relevant_ids), 10) + 1))
    return dcg / ideal if ideal else 0.0


def _recall_at_25(result_ids: list[str], relevant_ids: set[str]) -> float:
    return len(set(result_ids[:25]).intersection(relevant_ids)) / len(relevant_ids)


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * percentile) - 1)]
