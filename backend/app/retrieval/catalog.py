import json
import math
import re
import time
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, replace
from uuid import uuid4

from fastapi import HTTPException, status
from redis.asyncio import Redis
from redisvl.query import FilterQuery, TextQuery, VectorQuery
from redisvl.query.filter import Num, Tag

from app.config import Settings
from app.models.search import (
    AutocompleteResponse,
    ComparisonResponse,
    ProductResult,
    ProfileOption,
    PromotionOption,
    PublicConfigResponse,
    RedisSearchQuery,
    RerankerOption,
    RetailerPublicConfig,
    ScoreBreakdown,
    SearchFilters,
    SearchRequest,
    SearchResponse,
    SearchSuggestion,
    TenantOption,
)
from app.policy import PolicyContext, PolicyService
from app.redis.catalog_index import CatalogIndex
from app.reranking import RerankerError, RerankerProvider
from app.retailers import RETAILERS, RetailerDefinition
from app.routing import RoutingDecision, RoutingService

RETURN_FIELDS = [
    "id",
    "brand_name",
    "description",
    "categories",
    "aliases",
    "occasions",
    "recipient_tags",
    "delivery_types",
    "min_denomination",
    "max_denomination",
]


def normalize_text_query(query: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", query.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def split_tags(value: str | None) -> list[str]:
    return [tag for tag in (value or "").split("|") if tag]


def reciprocal_rank_fusion(rank: int, rrf_k: int) -> float:
    return 1 / (rrf_k + rank)


@dataclass
class Candidate:
    document: dict[str, object]
    lexical_rank: int | None = None
    lexical_score: float | None = None
    vector_rank: int | None = None
    vector_distance: float | None = None
    hybrid_score: float = 0.0
    reranker_score: float | None = None
    exact_match: bool = False
    prefix_match: bool = False


@dataclass
class HybridStage:
    candidates: list[Candidate]
    normalized_query: str
    timings: dict[str, float]
    diagnostics: dict[str, str | int | bool]
    redis_search_queries: list[RedisSearchQuery]
    fallbacks: list[str]


class CatalogService:
    def __init__(
        self,
        settings: Settings,
        redis_client: Redis,
        retailer: RetailerDefinition | None = None,
    ) -> None:
        self._settings = settings
        self._redis = redis_client
        self.retailer = retailer or settings.retailer
        self._keyspace = self.retailer.redis
        self.index = CatalogIndex(settings, redis_client, self.retailer)
        self._embeddings = None
        self._reranker = None
        self._routing = None
        self._policy = PolicyService(settings, redis_client, self.retailer)
        self._reranked_latencies: dict[str, deque[float]] = {}

    async def reset(self) -> None:
        await self.index.reset()
        await self._routing_service().reset()
        await self._delete_namespace_keys(self._keyspace)

    async def cleanup_legacy_namespaces(self) -> None:
        """Remove the pre-isolation BHN demo state after a namespace migration."""
        for namespace in self.retailer.legacy_namespaces:
            if namespace == self._keyspace:
                continue
            legacy_retailer = replace(self.retailer, redis=namespace, legacy_namespaces=())
            legacy_index = CatalogIndex(self._settings, self._redis, legacy_retailer)
            await legacy_index.reset()
            legacy_routing = RoutingService(self._settings, legacy_retailer)
            try:
                await legacy_routing.reset()
            finally:
                await legacy_routing.close()
            await self._delete_namespace_keys(namespace)

    async def close(self) -> None:
        if self._routing is not None:
            await self._routing.close()

    async def seed(
        self,
        records: list[dict[str, object]],
        tenant_records: Iterable[dict[str, object]],
        profile_records: Iterable[dict[str, object]],
        promotion_records: Iterable[dict[str, object]],
    ) -> int:
        await self.index.ensure_created()
        await self._store_json(self._keyspace.key("tenant"), tenant_records)
        await self._store_json(self._keyspace.key("profile"), profile_records)
        await self._store_json(self._keyspace.key("promotion"), promotion_records)
        await self._embedding_service().embed_catalog(records)
        await self.index.load(records)
        await self._routing_service().ensure_initialized()
        return await self.index.count()

    async def public_config(
        self, retailers: Iterable[RetailerDefinition] | None = None
    ) -> PublicConfigResponse:
        tenant_values = await self._read_json_pattern(self._keyspace.pattern("tenant", "*"))
        profile_values = await self._read_json_pattern(self._keyspace.pattern("profile", "*"))
        promotion_values = await self._read_json_pattern(self._keyspace.pattern("promotion", "*"))
        tenants = [
            TenantOption(
                id=tenant["id"],
                display_name=tenant["display_name"],
                allowed_delivery_types=tenant["allowed_delivery_types"],
                promotion_ids=tenant.get("promotion_ids", []),
            )
            for tenant in tenant_values
        ]
        return PublicConfigResponse(
            retailer=RetailerPublicConfig(
                id=self.retailer.id,
                organization_name=self.retailer.organization_name,
                experience_name=self.retailer.experience_name,
                experience_subtitle=self.retailer.experience_subtitle,
                catalog_label=self.retailer.catalog_label,
                theme=self.retailer.theme,
                demo_prompts=self.retailer.demo_prompts,
            ),
            retailers=[
                RetailerPublicConfig(
                    id=retailer.id,
                    organization_name=retailer.organization_name,
                    experience_name=retailer.experience_name,
                    experience_subtitle=retailer.experience_subtitle,
                    catalog_label=retailer.catalog_label,
                    theme=retailer.theme,
                    demo_prompts=retailer.demo_prompts,
                )
                for retailer in sorted(
                    retailers or RETAILERS.values(), key=lambda retailer: retailer.id
                )
            ],
            tenants=sorted(tenants, key=lambda tenant: tenant.id),
            profiles=sorted(
                [
                    ProfileOption(id=profile["id"], display_name=profile["display_name"])
                    for profile in profile_values
                ],
                key=lambda profile: profile.id,
            ),
            promotions=sorted(
                [
                    PromotionOption(
                        id=promotion["id"],
                        display_name=promotion["display_name"],
                        eligible_tenant_ids=promotion["eligible_tenant_ids"],
                    )
                    for promotion in promotion_values
                ],
                key=lambda promotion: promotion.id,
            ),
            rerankers=[
                RerankerOption(
                    id=preset.id,
                    display_name=preset.display_name,
                    provider=preset.provider,
                    model=preset.model,
                )
                for preset in self._reranker_provider().presets
            ],
            modes=["baseline", "hybrid", "reranked", "compare"],
            catalog_count=await self.index.count(),
            disclaimer=self.retailer.disclaimer,
        )

    async def search(self, request: SearchRequest) -> SearchResponse | ComparisonResponse:
        policy_context = await self._policy.load_context(
            request.tenant_id, request.profile_id, request.promotion_id
        )
        routing = await self._routing_service().route(request.query)
        if routing.action is not None:
            return self._action_response(request, routing)

        if request.mode == "compare":
            baseline_request = request.model_copy(update={"mode": "baseline"})
            hybrid_request = request.model_copy(update={"mode": "hybrid"})
            reranked_request = request.model_copy(update={"mode": "reranked"})
            baseline = await self.baseline_search(baseline_request)
            hybrid = await self.hybrid_search(hybrid_request)
            reranked = await self.reranked_search(reranked_request)
            for response in (baseline, hybrid, reranked):
                self._apply_policy(response, policy_context)
                self._apply_routing(response, routing)
            return ComparisonResponse(
                request_id=str(uuid4()),
                query=request.query,
                mode="compare",
                comparisons={"baseline": baseline, "hybrid": hybrid, "reranked": reranked},
            )
        if request.mode == "baseline":
            response = await self.baseline_search(request)
        elif request.mode == "reranked":
            response = await self.reranked_search(request)
        else:
            response = await self.hybrid_search(request)
        self._apply_policy(response, policy_context)
        self._apply_routing(response, routing)
        return response

    async def autocomplete(self, query: str, tenant_id: str, limit: int) -> AutocompleteResponse:
        await self._get_tenant_or_404(tenant_id)
        normalized_query = normalize_text_query(query)
        if not normalized_query:
            return AutocompleteResponse(query=query)
        request = SearchRequest(query=query, tenant_id=tenant_id, limit=limit)
        documents, redis_search_query = await self._prefix_documents(
            request, normalized_query, limit
        )
        return AutocompleteResponse(
            query=query,
            suggestions=[
                SearchSuggestion(
                    id=self._document_id(document),
                    brand_name=str(document.get("brand_name", "")),
                )
                for document in documents
            ],
            redis_search_query=redis_search_query,
        )

    async def baseline_search(self, request: SearchRequest) -> SearchResponse:
        started_at = time.perf_counter()
        normalized_query = await self._validated_query(request)
        retrieval_started_at = time.perf_counter()
        documents, redis_search_query = await self._lexical_documents(
            request, normalized_query, request.limit
        )
        prefix_documents, prefix_query = await self._prefix_documents(
            request, normalized_query, request.limit
        )
        retrieval_ms = (time.perf_counter() - retrieval_started_at) * 1_000
        candidates = self._protect_prefix_matches(
            [
                Candidate(document=document, lexical_rank=rank, lexical_score=_score(document))
                for rank, document in enumerate(documents, start=1)
            ],
            prefix_documents,
        )
        return self._response(
            request,
            candidates,
            timings={
                "retrieval": retrieval_ms,
                "total_server": (time.perf_counter() - started_at) * 1_000,
            },
            diagnostics={
                "retrieval": "redisvl_text_query",
                "normalized_query": normalized_query,
                "prefix_match_protection": bool(prefix_documents),
            },
            redis_search_queries=[
                redis_search_query,
                *([prefix_query] if prefix_query is not None else []),
            ],
        )

    async def hybrid_search(self, request: SearchRequest) -> SearchResponse:
        started_at = time.perf_counter()
        stage = await self._hybrid_stage(request)
        return self._response(
            request,
            stage.candidates[: request.limit],
            timings={
                **stage.timings,
                "total_server": (time.perf_counter() - started_at) * 1_000,
            },
            diagnostics=stage.diagnostics,
            redis_search_queries=stage.redis_search_queries,
            fallbacks=stage.fallbacks,
        )

    async def reranked_search(self, request: SearchRequest) -> SearchResponse:
        started_at = time.perf_counter()
        stage = await self._hybrid_stage(request)
        reranking_started_at = time.perf_counter()
        fallbacks = list(stage.fallbacks)
        reranker = self._reranker_provider()
        try:
            preset = reranker.preset_for(request.reranker_id)
            reranker_was_ready = reranker.is_ready(request.reranker_id)
            candidates = await self._rerank_candidates(
                stage.normalized_query, stage.candidates, request.reranker_id
            )
        except RerankerError as exc:
            candidates = stage.candidates
            fallbacks.append(exc.code)
            preset = None
            reranker_was_ready = False
        diagnostics = {
            **stage.diagnostics,
            "reranker_provider": preset.provider if preset else self._settings.reranker_provider,
            "reranker_id": request.reranker_id,
            "reranker_model": preset.model if preset else "unavailable",
            "rerank_top_n": self._settings.rerank_top_n,
        }
        response = self._response(
            request,
            candidates[: request.limit],
            timings={
                **stage.timings,
                "reranking": (time.perf_counter() - reranking_started_at) * 1_000,
                "total_server": (time.perf_counter() - started_at) * 1_000,
            },
            diagnostics=diagnostics,
            redis_search_queries=stage.redis_search_queries,
            fallbacks=fallbacks,
        )
        if not fallbacks and reranker_was_ready:
            self._reranked_latencies.setdefault(request.reranker_id, deque(maxlen=100)).append(
                response.timings_ms["total_server"]
            )
        if response.diagnostics is not None and self._reranked_latencies.get(request.reranker_id):
            response.diagnostics["warm_p95_ms"] = self._warm_p95_ms(request.reranker_id)
        return response

    async def _hybrid_stage(self, request: SearchRequest) -> HybridStage:
        normalized_query = await self._validated_query(request)
        candidate_count = max(request.limit, self._settings.search_candidate_count)

        lexical_started_at = time.perf_counter()
        lexical_documents, lexical_query = await self._lexical_documents(
            request, normalized_query, candidate_count
        )
        prefix_documents, prefix_query = await self._prefix_documents(
            request, normalized_query, candidate_count
        )
        lexical_ms = (time.perf_counter() - lexical_started_at) * 1_000

        embedding_started_at = time.perf_counter()
        try:
            embedding = await self._embedding_service().embed_query(normalized_query)
        except Exception:
            candidates = self._protect_prefix_matches(
                [
                    Candidate(document=document, lexical_rank=rank, lexical_score=_score(document))
                    for rank, document in enumerate(lexical_documents[: request.limit], start=1)
                ],
                prefix_documents,
            )
            return HybridStage(
                candidates=candidates,
                normalized_query=normalized_query,
                timings={
                    "embedding": (time.perf_counter() - embedding_started_at) * 1_000,
                    "lexical_retrieval": lexical_ms,
                },
                diagnostics={"retrieval": "lexical_fallback", "normalized_query": normalized_query},
                redis_search_queries=[
                    lexical_query,
                    *([prefix_query] if prefix_query is not None else []),
                ],
                fallbacks=["embedding_failed"],
            )
        embedding_ms = (time.perf_counter() - embedding_started_at) * 1_000

        vector_started_at = time.perf_counter()
        try:
            vector_documents, vector_query = await self._vector_documents(
                request, embedding, candidate_count
            )
        except Exception:
            candidates = self._protect_prefix_matches(
                [
                    Candidate(document=document, lexical_rank=rank, lexical_score=_score(document))
                    for rank, document in enumerate(lexical_documents[: request.limit], start=1)
                ],
                prefix_documents,
            )
            return HybridStage(
                candidates=candidates,
                normalized_query=normalized_query,
                timings={
                    "embedding": embedding_ms,
                    "lexical_retrieval": lexical_ms,
                },
                diagnostics={"retrieval": "lexical_fallback", "normalized_query": normalized_query},
                redis_search_queries=[
                    lexical_query,
                    *([prefix_query] if prefix_query is not None else []),
                ],
                fallbacks=["vector_search_failed"],
            )
        vector_ms = (time.perf_counter() - vector_started_at) * 1_000

        candidates = self._fuse(lexical_documents, vector_documents)
        candidates = self._protect_prefix_matches(candidates, prefix_documents)
        exact_documents, exact_query = await self._exact_documents(request, normalized_query)
        candidates = self._protect_exact_matches(candidates, exact_documents)
        return HybridStage(
            candidates=candidates,
            normalized_query=normalized_query,
            timings={
                "embedding": embedding_ms,
                "lexical_retrieval": lexical_ms,
                "vector_retrieval": vector_ms,
                "retrieval": lexical_ms + vector_ms,
            },
            diagnostics={
                "retrieval": "redisvl_text_and_vector_rrf",
                "normalized_query": normalized_query,
                "index_alias": self._keyspace.catalog_index_alias,
                "candidate_count": len(candidates),
                "exact_match_protection": any(candidate.exact_match for candidate in candidates),
                "prefix_match_protection": any(candidate.prefix_match for candidate in candidates),
            },
            redis_search_queries=[
                lexical_query,
                *([prefix_query] if prefix_query is not None else []),
                vector_query,
                exact_query,
            ],
            fallbacks=[],
        )

    async def _validated_query(self, request: SearchRequest) -> str:
        await self._get_tenant_or_404(request.tenant_id)
        normalized_query = normalize_text_query(request.query)
        if not normalized_query:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Query is empty"
            )
        return normalized_query

    async def _lexical_documents(
        self, request: SearchRequest, normalized_query: str, num_results: int
    ) -> tuple[list[dict[str, object]], RedisSearchQuery]:
        query = TextQuery(
            text=normalized_query,
            text_field_name={
                "brand_name": 4.0,
                "aliases": 3.0,
                "description": 1.0,
                "embedding_text": 0.5,
            },
            filter_expression=self._filters(request.tenant_id, request.filters),
            return_fields=RETURN_FIELDS,
            num_results=num_results,
            stopwords=None,
        )
        return await self.index.query_index.query(query), self._trace_query("Full-text", query)

    async def _vector_documents(
        self, request: SearchRequest, embedding: list[float], num_results: int
    ) -> tuple[list[dict[str, object]], RedisSearchQuery]:
        query = VectorQuery(
            vector=embedding,
            vector_field_name="embedding",
            filter_expression=self._filters(request.tenant_id, request.filters),
            return_fields=RETURN_FIELDS,
            num_results=num_results,
            normalize_vector_distance=True,
        )
        return await self.index.query_index.query(query), self._trace_query(
            "Vector KNN",
            query,
            parameters=[f"vector: FLOAT32[{len(embedding)}] query embedding"],
        )

    async def _prefix_documents(
        self, request: SearchRequest, normalized_query: str, num_results: int
    ) -> tuple[list[dict[str, object]], RedisSearchQuery | None]:
        if not request.prefix_matching or not _is_partial_brand_query(normalized_query):
            return [], None
        query = FilterQuery(
            filter_expression=self._filters(request.tenant_id, request.filters)
            & (Tag("brand_alias_prefixes") == normalized_query),
            return_fields=RETURN_FIELDS,
            num_results=num_results,
        )
        return await self.index.query_index.query(query), self._trace_query(
            "Brand and alias prefix fill", query
        )

    async def _exact_documents(
        self, request: SearchRequest, normalized_query: str
    ) -> tuple[list[dict[str, object]], RedisSearchQuery]:
        filter_expression = self._filters(request.tenant_id, request.filters) & (
            (Tag("normalized_brand") == normalized_query)
            | (Tag("exact_aliases") == normalized_query)
        )
        query = FilterQuery(
            filter_expression=filter_expression,
            return_fields=RETURN_FIELDS,
            num_results=self._settings.search_candidate_count,
        )
        return await self.index.query_index.query(query), self._trace_query(
            "Exact brand and alias guardrail", query
        )

    def _fuse(
        self, lexical_documents: list[dict[str, object]], vector_documents: list[dict[str, object]]
    ) -> list[Candidate]:
        candidates: dict[str, Candidate] = {}
        for rank, document in enumerate(lexical_documents, start=1):
            candidate = candidates.setdefault(
                self._document_id(document), Candidate(document=document)
            )
            candidate.lexical_rank = rank
            candidate.lexical_score = _score(document)
            candidate.hybrid_score += reciprocal_rank_fusion(rank, self._settings.search_rrf_k)
        for rank, document in enumerate(vector_documents, start=1):
            candidate = candidates.setdefault(
                self._document_id(document), Candidate(document=document)
            )
            candidate.vector_rank = rank
            candidate.vector_distance = _vector_distance(document)
            candidate.hybrid_score += reciprocal_rank_fusion(rank, self._settings.search_rrf_k)
        return sorted(
            candidates.values(), key=lambda candidate: candidate.hybrid_score, reverse=True
        )

    def _protect_exact_matches(
        self, candidates: list[Candidate], exact_documents: list[dict[str, object]]
    ) -> list[Candidate]:
        candidate_by_id = {
            self._document_id(candidate.document): candidate for candidate in candidates
        }
        exact_ids = {self._document_id(document) for document in exact_documents}
        for document in exact_documents:
            candidate = candidate_by_id.setdefault(
                self._document_id(document), Candidate(document=document)
            )
            candidate.exact_match = True
        candidates = list(candidate_by_id.values())
        for candidate in candidates:
            candidate.exact_match = self._document_id(candidate.document) in exact_ids
        return sorted(
            candidates,
            key=lambda candidate: (
                not candidate.exact_match,
                not candidate.prefix_match,
                -candidate.hybrid_score,
            ),
        )

    def _protect_prefix_matches(
        self, candidates: list[Candidate], prefix_documents: list[dict[str, object]]
    ) -> list[Candidate]:
        candidate_by_id = {
            self._document_id(candidate.document): candidate for candidate in candidates
        }
        prefix_ids = {self._document_id(document) for document in prefix_documents}
        for document in prefix_documents:
            candidate = candidate_by_id.setdefault(
                self._document_id(document), Candidate(document=document)
            )
            candidate.prefix_match = True
        candidates = list(candidate_by_id.values())
        for candidate in candidates:
            candidate.prefix_match = self._document_id(candidate.document) in prefix_ids
        return sorted(
            candidates,
            key=lambda candidate: (
                not candidate.prefix_match,
                candidate.lexical_rank is None,
                -(candidate.lexical_score or 0),
                -candidate.hybrid_score,
            ),
        )

    async def _rerank_candidates(
        self, query: str, candidates: list[Candidate], reranker_id: str
    ) -> list[Candidate]:
        rerankable = [replace(candidate) for candidate in candidates[: self._settings.rerank_top_n]]
        ranked = await self._reranker_provider().rank(
            query,
            [
                {
                    "id": self._document_id(candidate.document),
                    "content": _rerank_text(candidate.document),
                }
                for candidate in rerankable
            ],
            reranker_id,
        )
        candidate_by_id = {
            self._document_id(candidate.document): candidate for candidate in rerankable
        }
        reranked_candidates: list[Candidate] = []
        for candidate_id, raw_score in ranked:
            candidate = candidate_by_id[candidate_id]
            candidate.reranker_score = _normalize_reranker_score(raw_score)
            reranked_candidates.append(candidate)

        reranked_ids = {self._document_id(candidate.document) for candidate in reranked_candidates}
        reranked_candidates.extend(
            replace(candidate)
            for candidate in candidates
            if self._document_id(candidate.document) not in reranked_ids
        )
        return sorted(
            reranked_candidates,
            key=lambda candidate: (
                not candidate.exact_match,
                not candidate.prefix_match,
                candidate.reranker_score is None,
                -(
                    candidate.reranker_score
                    if candidate.reranker_score is not None
                    else candidate.hybrid_score
                ),
            ),
        )

    def _reranker_provider(self) -> RerankerProvider:
        if self._reranker is None:
            self._reranker = RerankerProvider(self._settings)
        return self._reranker

    def reranker_preset(self, reranker_id: str):
        return self._reranker_provider().preset_for(reranker_id)

    def _routing_service(self) -> RoutingService:
        if self._routing is None:
            self._routing = RoutingService(self._settings, self.retailer)
        return self._routing

    def _apply_policy(self, response: SearchResponse, context: PolicyContext) -> None:
        started_at = time.perf_counter()
        response.results = self._policy.apply(response.results, context)
        policy_ms = round((time.perf_counter() - started_at) * 1_000, 2)
        response.timings_ms["policy"] = policy_ms
        response.timings_ms["total_server"] = round(
            response.timings_ms.get("total_server", 0.0) + policy_ms, 2
        )
        if response.diagnostics is not None:
            response.diagnostics.update(
                {
                    "profile_id": context.profile_id,
                    "promotion_id": context.promotion.get("id") if context.promotion else "none",
                    "policy": "bounded_personalization_and_merchandising",
                }
            )

    def _action_response(self, request: SearchRequest, routing: RoutingDecision) -> SearchResponse:
        return SearchResponse(
            request_id=str(uuid4()),
            query=request.query,
            mode="hybrid",
            results=[],
            timings_ms={
                "routing": round(routing.timing_ms, 2),
                "total_server": round(routing.timing_ms, 2),
            },
            intent=routing.intent,
            action=routing.action,
            diagnostics={"routing": "redisvl_semantic_router"} if request.debug else None,
        )

    @staticmethod
    def _apply_routing(response: SearchResponse, routing: RoutingDecision) -> None:
        response.intent = routing.intent
        routing_ms = round(routing.timing_ms, 2)
        response.timings_ms["routing"] = routing_ms
        response.timings_ms["total_server"] = round(
            response.timings_ms.get("total_server", 0.0) + routing_ms, 2
        )
        # A low-confidence service route is the expected outcome for ordinary product searches.
        # Keep it in the routing decision, but do not treat it as retrieval degradation.
        if routing.intent.fallback and routing.intent.source != "router_low_confidence":
            response.fallbacks = [routing.intent.source, *response.fallbacks]

    def _warm_p95_ms(self, reranker_id: str) -> float:
        ordered = sorted(self._reranked_latencies[reranker_id])
        index = max(0, math.ceil(len(ordered) * 0.95) - 1)
        return ordered[index]

    def _trace_query(
        self, label: str, query: object, parameters: list[str] | None = None
    ) -> RedisSearchQuery:
        return RedisSearchQuery(
            label=label,
            statement=f"FT.SEARCH {self._keyspace.catalog_index_alias} {query}",
            parameters=parameters or [],
        )

    def _response(
        self,
        request: SearchRequest,
        candidates: list[Candidate],
        *,
        timings: dict[str, float],
        diagnostics: dict[str, str | int | bool | float],
        redis_search_queries: list[RedisSearchQuery],
        fallbacks: list[str] | None = None,
    ) -> SearchResponse:
        normalized_query = normalize_text_query(request.query)
        results = [
            self._to_result(candidate, rank, normalized_query)
            for rank, candidate in enumerate(candidates, start=1)
        ]
        return SearchResponse(
            request_id=str(uuid4()),
            query=request.query,
            mode=request.mode,
            results=results,
            timings_ms={name: round(value, 2) for name, value in timings.items()},
            redis_search_queries=redis_search_queries,
            diagnostics={**diagnostics, "candidate_count": len(candidates)}
            if request.debug
            else None,
            fallbacks=fallbacks or [],
        )

    def _to_result(self, candidate: Candidate, rank: int, normalized_query: str) -> ProductResult:
        document = candidate.document
        return ProductResult(
            id=self._document_id(document),
            brand_name=str(document.get("brand_name", "")),
            description=str(document.get("description", "")),
            categories=split_tags(str(document.get("categories", ""))),
            delivery_types=split_tags(str(document.get("delivery_types", ""))),
            min_denomination=int(float(str(document.get("min_denomination", 0)))),
            max_denomination=int(float(str(document.get("max_denomination", 0)))),
            popularity_score=float(str(document.get("popularity_score", 0))),
            score=(
                candidate.reranker_score
                if candidate.reranker_score is not None
                else candidate.hybrid_score or candidate.lexical_score
            ),
            score_breakdown=ScoreBreakdown(
                lexical_score=candidate.lexical_score,
                lexical_rank=candidate.lexical_rank,
                vector_distance=candidate.vector_distance,
                vector_rank=candidate.vector_rank,
                hybrid_score=candidate.hybrid_score or None,
                reranker_score=candidate.reranker_score,
                matching_fields=_matching_fields(document, normalized_query),
                exact_match=candidate.exact_match,
                prefix_match=candidate.prefix_match,
            ),
        )

    def _filters(self, tenant_id: str, filters: SearchFilters):
        expression = (Tag("tenant_ids") == tenant_id) & (Tag("active") == "true")
        if filters.country:
            expression = expression & (Tag("country") == filters.country.upper())
        if filters.currency:
            expression = expression & (Tag("currency") == filters.currency.upper())
        if filters.category:
            expression = expression & (Tag("categories") == filters.category.lower())
        if filters.delivery_types:
            expression = expression & (Tag("delivery_types") == filters.delivery_types)
        if filters.min_denomination is not None:
            expression = expression & (Num("max_denomination") >= filters.min_denomination)
        if filters.max_denomination is not None:
            expression = expression & (Num("min_denomination") <= filters.max_denomination)
        return expression

    def _embedding_service(self):
        if self._embeddings is None:
            from app.retrieval.embeddings import EmbeddingService

            self._embeddings = EmbeddingService(self._settings, self._redis, self.retailer)
        return self._embeddings

    def _document_id(self, document: dict[str, object]) -> str:
        return _document_id(document, self._keyspace.catalog_document_prefix)

    async def _get_tenant_or_404(self, tenant_id: str) -> dict[str, object]:
        value = await self._redis.get(self._keyspace.key("tenant", tenant_id))
        if value is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown tenant: {tenant_id}"
            )
        return json.loads(value)

    async def _store_json(self, prefix: str, records: Iterable[dict[str, object]]) -> None:
        pipeline = self._redis.pipeline(transaction=False)
        for record in records:
            pipeline.set(f"{prefix}:{record['id']}", json.dumps(record, separators=(",", ":")))
        await pipeline.execute()

    async def _read_json_pattern(self, pattern: str) -> list[dict[str, object]]:
        values: list[dict[str, object]] = []
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
            if keys:
                values.extend(
                    json.loads(value) for value in await self._redis.mget(keys) if value is not None
                )
            if cursor == 0:
                return values

    async def _delete_namespaced_keys(self, patterns: Iterable[str]) -> None:
        for pattern in patterns:
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self._redis.delete(*keys)
                if cursor == 0:
                    break

    async def _delete_namespace_keys(self, namespace) -> None:
        await self._delete_namespaced_keys(
            (
                namespace.pattern(namespace.catalog_key_segment, "*"),
                namespace.pattern("tenant", "*"),
                namespace.pattern("profile", "*"),
                namespace.pattern("promotion", "*"),
                namespace.pattern("search", "event", "*"),
                namespace.pattern("evaluation", "*"),
                namespace.pattern("evaluation-load", "*"),
                namespace.pattern("cache", "embedding", "*"),
                namespace.pattern("runtime", "*"),
                f"{namespace.router_name}:*",
            )
        )


def _document_id(document: dict[str, object], catalog_prefix: str) -> str:
    return str(document.get("id", "")).removeprefix(f"{catalog_prefix}:")


def _is_partial_brand_query(normalized_query: str) -> bool:
    return 3 <= len(normalized_query) <= 40 and len(normalized_query.split()) <= 3


def _score(document: dict[str, object]) -> float | None:
    score = document.get("score")
    return float(score) if score is not None else None


def _vector_distance(document: dict[str, object]) -> float | None:
    distance = document.get("vector_distance")
    return float(distance) if distance is not None else None


def _rerank_text(document: dict[str, object]) -> str:
    fields = ("brand_name", "aliases", "description", "categories", "occasions", "recipient_tags")
    return ". ".join(str(document.get(field, "")).replace("|", ", ") for field in fields)


EVIDENCE_STOPWORDS = frozenset(
    {"a", "an", "and", "child", "for", "from", "gift", "my", "the", "to"}
)


def _matching_fields(document: dict[str, object], normalized_query: str) -> list[str]:
    query_terms = {
        term
        for term in normalized_query.split()
        if len(term) > 2 and term not in EVIDENCE_STOPWORDS
    }
    field_labels = (
        ("brand_name", "brand"),
        ("aliases", "alias"),
        ("description", "description"),
        ("categories", "category"),
        ("occasions", "occasion"),
        ("recipient_tags", "recipient"),
    )
    matches: list[str] = []
    for field, label in field_labels:
        value = normalize_text_query(str(document.get(field, "")).replace("|", " "))
        terms = [term for term in query_terms if term in value]
        if terms:
            matches.append(f"{label}: {', '.join(sorted(terms)[:2])}")
    return matches


def _normalize_reranker_score(score: float) -> float:
    bounded_score = max(-60.0, min(60.0, score))
    return 1 / (1 + math.exp(-bounded_score))
