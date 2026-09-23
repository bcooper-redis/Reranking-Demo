import os

import pytest

from app.config import Settings
from app.models.search import SearchRequest
from app.redis import RedisClient
from app.retrieval import CatalogService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_seeded_catalog_searches_and_respects_tenant_filter() -> None:
    if os.getenv("RUN_REDIS_INTEGRATION") != "1":
        pytest.skip("Set RUN_REDIS_INTEGRATION=1 after seeding a Redis Query Engine instance")

    settings = Settings(rerank_timeout_ms=30_000)
    client = RedisClient(settings)
    try:
        service = CatalogService(settings, client.client)
        best_buy = await service.hybrid_search(SearchRequest(query="Best Buy", debug=True))
        assert best_buy.results[0].brand_name == "Best Buy"

        literal_star = await service.baseline_search(
            SearchRequest(query="Star", prefix_matching=False, debug=True)
        )
        assert literal_star.results[0].brand_name == "AMC Theatres eGift"
        assert literal_star.results[0].score_breakdown.prefix_match is False

        partial_brand = await service.hybrid_search(SearchRequest(query="Star", debug=True))
        assert partial_brand.results[0].brand_name == "Starbucks eGift"
        assert partial_brand.results[0].score_breakdown.prefix_match is True
        assert "Brand and alias prefix fill" in [
            query.label for query in partial_brand.redis_search_queries
        ]

        suggestions = await service.autocomplete("Star", "general", 5)
        assert [suggestion.brand_name for suggestion in suggestions.suggestions] == [
            "Starbucks eGift"
        ]
        assert suggestions.redis_search_query is not None
        assert suggestions.redis_search_query.label == "Brand and alias prefix fill"

        bank_results = await service.baseline_search(
            SearchRequest(query="coffee gift", tenant_id="bank_rewards")
        )
        for result in bank_results.results:
            assert "egift" in result.delivery_types

        discovery = await service.hybrid_search(
            SearchRequest(query="a thoughtful thank you for an educator")
        )
        assert discovery.results
        assert discovery.fallbacks == []
        assert any(result.score_breakdown.vector_rank is not None for result in discovery.results)
        assert any(
            result.score_breakdown.vector_distance is not None for result in discovery.results
        )
        assert [query.label for query in discovery.redis_search_queries] == [
            "Full-text",
            "Vector KNN",
            "Exact brand and alias guardrail",
        ]
        assert all(
            query.statement.startswith("FT.SEARCH demo:bhn:giftcards ")
            for query in discovery.redis_search_queries
        )
        assert discovery.redis_search_queries[1].parameters == [
            "vector: FLOAT32[384] query embedding"
        ]

        reranked_exact = await service.reranked_search(SearchRequest(query="Best Buy", debug=True))
        assert reranked_exact.results[0].brand_name == "Best Buy"
        assert reranked_exact.results[0].score_breakdown.exact_match is True
        assert reranked_exact.results[0].score_breakdown.reranker_score is not None
        assert reranked_exact.fallbacks == []
        assert reranked_exact.diagnostics is not None
        assert reranked_exact.diagnostics["reranker_provider"] == "local_hf"

        warm_reranked_exact = await service.reranked_search(
            SearchRequest(query="Best Buy", debug=True)
        )
        assert warm_reranked_exact.diagnostics is not None
        assert "warm_p95_ms" in warm_reranked_exact.diagnostics

        discovery_queries = [
            "a practical housewarming gift for a new homeowner",
            "a cozy thank you for a teacher who loves coffee",
            "a flexible graduation surprise for a movie fan",
        ]
        changed_orders = 0
        for query in discovery_queries:
            hybrid = await service.hybrid_search(SearchRequest(query=query))
            reranked = await service.reranked_search(SearchRequest(query=query))
            assert reranked.fallbacks == []
            assert all(
                result.score_breakdown.reranker_score is not None for result in reranked.results
            )
            changed_orders += [result.id for result in hybrid.results] != [
                result.id for result in reranked.results
            ]
        assert changed_orders == len(discovery_queries)

        unavailable_service = CatalogService(Settings(reranker_provider="none"), client.client)
        unavailable_hybrid = await unavailable_service.hybrid_search(
            SearchRequest(query="Best Buy")
        )
        unavailable_reranked = await unavailable_service.reranked_search(
            SearchRequest(query="Best Buy", debug=True)
        )
        assert unavailable_reranked.fallbacks == ["reranker_disabled"]
        assert [result.id for result in unavailable_reranked.results] == [
            result.id for result in unavailable_hybrid.results
        ]
        assert unavailable_reranked.diagnostics is not None
        assert unavailable_reranked.diagnostics["reranker_provider"] == "none"

        action_routes = {
            "check my balance": "balance_check",
            "activate this card": "card_activation",
            "where is my order": "order_status",
            "my card is not working": "customer_support",
        }
        for query, expected_intent in action_routes.items():
            action_response = await service.search(
                SearchRequest(query=query, mode="compare", debug=True)
            )
            assert action_response.mode == "hybrid"
            assert action_response.intent is not None
            assert action_response.intent.name == expected_intent
            assert action_response.intent.fallback is False
            assert action_response.intent.source == "redisvl_semantic_router"
            assert action_response.action is not None
            assert action_response.results == []

        product_response = await service.search(
            SearchRequest(query="coffee gift for my child's teacher", mode="baseline")
        )
        assert product_response.intent is not None
        assert product_response.intent.name == "product_search"
        assert product_response.action is None
        assert product_response.results

        unknown_response = await service.search(
            SearchRequest(query="zxqv blorf lumen", mode="baseline")
        )
        assert unknown_response.intent is not None
        assert unknown_response.intent.name == "product_search"
        assert unknown_response.action is None
    finally:
        await client.close()
