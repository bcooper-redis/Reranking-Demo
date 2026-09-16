# Technical Architecture and Interface Specification

## 1. System architecture

The application is a monorepo with these services:

- `frontend`: React/TypeScript single-page application.
- `api`: FastAPI application containing routing, retrieval, re-ranking, policy, diagnostics, and evaluation endpoints.
- `redis`: Redis 8.4+ for local development; replaceable with Redis Cloud or Redis Enterprise by environment configuration.
- `seed`: repeatable backend command or one-shot service that creates indexes and loads demo data.
- `loadtest`: optional profile containing Locust or k6 tests.

The runtime request path is:

1. Validate request and load tenant/profile context from Redis.
2. Use RedisVL SemanticRouter to classify the query.
3. For action intents, return a configured action response.
4. For product search, normalize the query and determine exact-brand candidates.
5. Execute tenant-filtered hybrid retrieval from Redis.
6. Re-rank the top N candidates through a RedisVL re-ranker.
7. Apply exact-match protection and bounded policy boosts.
8. Return final results with timings and optional diagnostics.
9. Asynchronously record a search event.

## 2. RedisVL requirements

RedisVL must be used directly for these capabilities where supported by the installed stable version:

- index schema definition and index lifecycle;
- query construction and filter expressions;
- query vectorization;
- `SemanticRouter` and route references;
- `HFCrossEncoderReranker` as the default local re-ranker;
- optional `CohereReranker` and `VoyageAIReranker` adapters;
- embedding cache if supported by the selected version; and
- result shaping into typed backend models.

Do not create a generic internal framework that merely resembles RedisVL. Wrap RedisVL only at clear boundaries needed for testing, configuration, provider selection, or fallback behavior.

If Redis 8.4+ and the RedisVL version expose native hybrid fusion, use it. Otherwise, execute lexical and vector retrieval separately and apply Reciprocal Rank Fusion in the application. The fallback must be documented and tested.

## 3. Package structure

Recommended layout:

```text
/
  README.md
  docker-compose.yml
  .env.example
  Makefile
  docs/
  backend/
    pyproject.toml
    app/
      api/
      config/
      models/
      redis/
      routing/
      retrieval/
      reranking/
      policy/
      evaluation/
      telemetry/
      main.py
    data/
      gift_cards.json
      tenants.json
      profiles.json
      routes.json
      judgments.json
    tests/
  frontend/
    package.json
    src/
      api/
      components/
      pages/
      state/
      types/
    tests/
  loadtest/
```

## 4. Redis key and index design

Use explicit prefixes and keep all demo keys namespaced.

| Purpose | Key pattern | Storage |
|---|---|---|
| Gift-card product | `demo:giftcard:{id}` | JSON preferred; Hash acceptable with justification |
| User/persona profile | `demo:profile:{id}` | JSON |
| Tenant configuration | `demo:tenant:{id}` | JSON |
| Promotion | `demo:promotion:{id}` | JSON |
| Support/action route | RedisVL-managed router keys with `demo:` namespace | Hash/RedisVL |
| Search event | `demo:search:event:{ulid}` | JSON or Stream |
| Evaluation run | `demo:evaluation:{ulid}` | JSON |
| Query/result cache | `demo:cache:search:{hash}` | String/JSON with TTL |

Primary search index alias: `demo:giftcards`

Versioned physical indexes:

- `demo:giftcards:v1`
- `demo:giftcards:v2`

Use alias switching for repeatable, zero-downtime reindex demonstrations.

## 5. Gift-card document schema

Every document must contain:

```json
{
  "id": "gc_001",
  "brand_name": "Best Buy",
  "normalized_brand": "best buy",
  "aliases": ["bestbuy", "best buy electronics"],
  "description": "Electronics, games, appliances and technology gifts.",
  "categories": ["electronics", "gaming", "home appliances"],
  "occasions": ["birthday", "graduation", "holiday"],
  "recipient_tags": ["tech lover", "gamer", "student"],
  "delivery_types": ["egift", "physical"],
  "country": "US",
  "currency": "USD",
  "min_denomination": 10,
  "max_denomination": 500,
  "tenant_ids": ["general", "bank_rewards"],
  "active": true,
  "popularity_score": 0.82,
  "conversion_score": 0.74,
  "margin_score": 0.45,
  "promotion_ids": [],
  "image_url": null,
  "embedding_text": "Best Buy. Electronics, gaming...",
  "embedding": []
}
```

Index fields:

- `brand_name`, `aliases`, `description`, and `embedding_text`: `TEXT` as appropriate.
- `normalized_brand`, `categories`, `occasions`, `recipient_tags`, `delivery_types`, `country`, `currency`, `tenant_ids`, and `active`: `TAG`.
- denominations and numeric ranking features: `NUMERIC`, sortable where returned or sorted.
- `embedding`: `VECTOR`, dimension and type matching the configured embedding model exactly.

Because the demo corpus is below 10,000 products, `FLAT` vector search is acceptable and provides exact nearest-neighbor results. Support `HNSW` through configuration to demonstrate production-oriented scaling.

## 6. Profile schema

```json
{
  "id": "tech_buyer",
  "display_name": "Tech Buyer",
  "category_affinities": {
    "electronics": 0.9,
    "gaming": 0.7
  },
  "brand_affinities": {
    "Best Buy": 0.8
  },
  "occasion_affinities": {},
  "recent_categories": ["electronics", "gaming"]
}
```

Profiles are synthetic. The Anonymous profile has no affinities.

## 7. Tenant schema

```json
{
  "id": "bank_rewards",
  "display_name": "Bank Rewards Portal",
  "country": "US",
  "currency": "USD",
  "allowed_delivery_types": ["egift"],
  "promotion_ids": ["promo_dining_week"],
  "policy": {
    "personalization_max_boost": 0.10,
    "promotion_max_boost": 0.08
  }
}
```

## 8. Retrieval design

### 8.1 Baseline mode

Implement deliberately simple but honest lexical search. It must not add artificial sleep. Measure real latency and show that the comparison is primarily about ranking quality if local latency differences are small.

If an OpenSearch service is not included, label this mode `Baseline lexical`, not `OpenSearch`. Never claim a measured OpenSearch comparison without running OpenSearch.

### 8.2 Hybrid mode

Hybrid retrieval must combine:

- exact and lexical matching;
- fuzzy or alias matching where appropriate;
- vector similarity; and
- pre-filters for tenant and product eligibility.

Return a candidate pool of 25 by default, configurable from 10 to 100.

Fusion defaults:

- Use Redis native `FT.HYBRID` with RRF when available.
- Otherwise combine lexical and vector ranks using RRF with configurable `k`, default 60.
- Preserve raw ranks and normalized scores for diagnostics.

### 8.3 Exact-match protection

Before final sorting, detect a normalized exact match against brand name or approved aliases.

Rules:

- Active and tenant-eligible exact matches must rank first.
- When several variants of one exact brand exist, use re-ranker and policy scores within that brand group.
- Exact-match protection must be explicit in the response diagnostics.

## 9. Semantic routing

Use RedisVL `SemanticRouter` with version-controlled route references.

Minimum routes:

```yaml
product_search:
  - "show me a gift card"
  - "I need a present for a teacher"
  - "Best Buy"
balance_check:
  - "check my balance"
  - "how much is left on my card"
card_activation:
  - "activate my card"
  - "my new card needs activation"
order_status:
  - "where is my order"
  - "track my gift card"
customer_support:
  - "I need help"
  - "my card is not working"
```

Each route has a configurable distance threshold. Exact navigation phrases may be recognized deterministically before semantic routing. Log both the selected route and confidence/distance.

## 10. Re-ranking

Define a `RerankerProvider` application interface with RedisVL-backed implementations:

- `local_hf` — required default using `HFCrossEncoderReranker`.
- `cohere` — optional when configured.
- `voyage` — optional when configured.
- `none` — fallback/testing.

The default re-ranker input should concatenate only fields relevant to query-product relevance:

- brand name;
- aliases;
- description;
- categories;
- occasions; and
- recipient tags.

Do not include margin or promotional values in the neural relevance text. Those belong in the policy stage.

Default top-N for re-ranking: 20. Configurable range: 5–50.

Apply a configurable timeout. On timeout or provider error, return hybrid ordering and record fallback metadata.

## 11. Policy scoring

Relevance and commercial policy must remain separate.

Suggested calculation after normalization:

```text
relevance = reranker_score when available, otherwise hybrid_score
personalization_boost = min(profile_affinity * 0.10, tenant.personalization_max_boost)
promotion_boost = min(relevant_promotion_score * 0.08, tenant.promotion_max_boost)
popularity_tiebreaker = popularity_score * 0.02
final_score = relevance + personalization_boost + promotion_boost + popularity_tiebreaker
```

Guardrails:

- Promotion applies only to candidates already retrieved as relevant.
- Total non-relevance boost is capped.
- Exact match protection runs after policy scoring.
- Every contribution is returned in debug mode.
- Weights live in configuration, not scattered constants.

## 12. API contract

### `POST /api/v1/search`

Request:

```json
{
  "query": "coffee gift for my teacher",
  "tenant_id": "general",
  "profile_id": "coffee_enthusiast",
  "mode": "reranked",
  "filters": {
    "country": "US",
    "currency": "USD",
    "delivery_types": ["egift"],
    "min_denomination": 10,
    "max_denomination": 100
  },
  "limit": 10,
  "debug": true
}
```

`mode` is one of `baseline`, `hybrid`, `reranked`, or `compare`.

Response:

```json
{
  "request_id": "01...",
  "query": "coffee gift for my teacher",
  "intent": {
    "name": "product_search",
    "confidence": 0.91,
    "fallback": false
  },
  "results": [
    {
      "id": "gc_123",
      "brand_name": "Example Coffee",
      "description": "...",
      "categories": ["coffee"],
      "delivery_types": ["egift"],
      "min_denomination": 10,
      "max_denomination": 100,
      "promoted": false,
      "score": 0.88,
      "score_breakdown": {
        "lexical_rank": 4,
        "vector_rank": 1,
        "hybrid_score": 0.73,
        "reranker_score": 0.84,
        "personalization_boost": 0.04,
        "promotion_boost": 0,
        "exact_match": false,
        "final_score": 0.88
      }
    }
  ],
  "timings_ms": {
    "routing": 3.1,
    "embedding": 7.4,
    "retrieval": 5.2,
    "reranking": 82.5,
    "policy": 0.7,
    "total_server": 101.8
  },
  "fallbacks": [],
  "diagnostics": {
    "candidate_count": 25,
    "reranker_provider": "local_hf",
    "index_alias": "demo:giftcards"
  }
}
```

For `compare`, return separate result sets and timings under `comparisons.baseline`, `comparisons.hybrid`, and `comparisons.reranked`.

### Other endpoints

- `GET /api/v1/config/public` — personas, tenants, modes, and UI-safe configuration.
- `POST /api/v1/events/click` — record a synthetic click.
- `POST /api/v1/admin/reindex` — development-only, protected by a local admin token.
- `POST /api/v1/admin/reset-events` — development-only.
- `POST /api/v1/evaluations/run` — run golden queries.
- `GET /api/v1/evaluations/{id}` — retrieve evaluation results.
- `GET /health/live` — process liveness.
- `GET /health/ready` — Redis, index, router, and model readiness.

## 13. Configuration

Required environment variables:

```dotenv
REDIS_URL=redis://redis:6379
REDIS_INDEX_ALIAS=demo:giftcards
EMBEDDING_PROVIDER=local_hf
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RERANKER_PROVIDER=local_hf
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RERANK_TOP_N=20
RERANK_TIMEOUT_MS=250
SEARCH_LIMIT_DEFAULT=10
SEARCH_CANDIDATE_COUNT=25
ENABLE_DEBUG=true
ADMIN_TOKEN=change-me
```

Optional provider credentials must be documented but left blank.

## 14. Caching

- Cache document embeddings during ingestion.
- Cache query embeddings by normalized query and embedding-model version with a bounded TTL.
- Optionally cache anonymous search results by tenant, filters, mode, and index version.
- Do not cache personalized responses without profile ID and profile version in the key.
- Expose cache hits in diagnostics.

## 15. Observability

Use structured JSON logs containing request ID, tenant, mode, intent, candidate count, provider, fallbacks, and stage timings. Never log secrets.

Expose basic application metrics:

- request count and error count;
- latency histogram by mode and stage;
- fallback count;
- route distribution;
- cache hit ratio; and
- re-ranker provider errors.

OpenTelemetry support is desirable but not required for the first demo milestone.

## 16. Data generation

Seed at least 300 gift-card documents by default and support generation of 1,500. Include enough overlap for ranking to be meaningful across retail, electronics, restaurants, coffee, travel, gaming, grocery, entertainment, home improvement, beauty, and general-purpose categories.

Use either fictional brands or clearly marked demo records. Do not scrape Giftcards.com or copy protected descriptions or logos. Familiar merchant names may appear only in a small manually authored internal-demo fixture without logos, accompanied by the no-affiliation disclaimer.

## 17. Failure behavior

| Failure | Required behavior |
|---|---|
| Redis unavailable | Return 503 readiness failure; UI displays actionable error |
| Router unavailable | Use deterministic intent rules, then product-search fallback |
| Embedding failure | Use lexical retrieval |
| Vector search failure | Use lexical retrieval |
| Re-ranker timeout/error | Return hybrid order |
| Profile missing | Use Anonymous profile |
| Tenant missing | Return validation error; never silently broaden catalog |
| No eligible results | Return empty state and suggested query changes |

