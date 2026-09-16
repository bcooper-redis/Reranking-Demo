# GiftFind RedisVL Relevance Lab

GiftFind is a local web demo for Blackhawk Network conversations. It shows how Redis and RedisVL can serve gift-card discovery, hybrid lexical plus semantic retrieval, neural re-ranking, intent routing, bounded personalization, tenant merchandising, and evaluation from one real-time relevance platform.

The catalog pairs a curated public GiftCards.com assortment snapshot with synthetic relevance-lab variants; personas, tenants, promotions, and events are synthetic. The snapshot is intentionally static, so availability, denominations, and fulfillment in this demo are not a live commerce feed.

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- Readiness: http://localhost:8000/health/ready

The `seed` service prepares Redis before the API starts. During Milestone 0 it verifies Redis connectivity and initializes the demo runtime namespace; catalog indexing and local-model downloads arrive in Milestone 1.

## Implementation Status

- [x] Milestone 0: local runtime, health endpoints, Docker images, quality commands, and CI.
- [x] Milestone 1: catalog generation, RedisVL index, seed data, and baseline search.
- [x] Milestone 2: hybrid retrieval and comparison.
- [x] Milestone 3: RedisVL re-ranking.
- [x] Milestone 4: semantic routing.
- [x] Milestone 5: personalization and merchandising.
- [x] Milestone 6: evaluation, telemetry, and presenter polish.
- [x] Milestone 7: bounded concurrent load testing and steady-state latency reporting.

Milestone 2 generates local Hugging Face embeddings with RedisVL during seed, caches normalized query embeddings in Redis, runs tenant-filtered lexical and vector retrieval, and fuses the ranked candidates with Reciprocal Rank Fusion. Exact active brand and alias matches are guarded at rank one after fusion.

Milestone 3 re-scores the top hybrid candidates with RedisVL's local Hugging Face cross-encoder. Re-ranker scores are normalized, exact matches remain protected, and timeout or provider failures return the hybrid order with explicit fallback metadata. Comparison mode shows baseline, hybrid, and re-ranked columns, including stage and rolling warm-p95 timing diagnostics.

The application default remains a conservative 250 ms re-ranker timeout. The CPU-only Docker demo uses a 3-second budget unless `RERANK_TIMEOUT_MS` is set, so the warmed local cross-encoder can be shown during a presentation.

Milestone 4 routes each query through RedisVL `SemanticRouter`, using version-controlled references stored under `demo:routes`. Confident balance, activation, order-status, and support intents return a simulated action card. Low-confidence or unavailable-router decisions fall back safely to product search, with the selected intent, distance, threshold, source, and timing shown in the demo panel.

Milestone 5 loads synthetic personas, tenant policy caps, and tenant-eligible promotions from Redis on each request. It applies bounded boosts only after retrieval, exposes every contribution on result cards, and runs exact-brand protection after policy scoring. Promotions only affect candidates already returned by relevance retrieval and only when their category is eligible.

Milestone 6 adds a version-controlled golden-query scorecard for baseline, hybrid, and re-ranked paths. Each run reports Hit@1, MRR, NDCG@10, Recall@25, route accuracy, and p50/p95 latency, then saves its index and model configuration under `demo:evaluation:*`. The UI includes presenter scenes, compact synthetic event telemetry, and result-selection capture under `demo:search:event:*`.

Milestone 7 adds a bounded load test alongside the scorecard. After one normal re-ranked request warms the selected local cross-encoder, the UI runs four product judgments through baseline, hybrid, and re-ranked retrieval three times each. At concurrency `2`, each mode records 12 requests while allowing two requests to overlap; the resulting p50 and p95 distinguish steady-state performance from initial model loading. The report also separates safe routing fallbacks from failed requests. Use concurrency `4` only as a local CPU-pressure observation, not as a production capacity benchmark. Every run retains the selected re-ranker configuration and is saved under `demo:evaluation-load:*`.

The brand and alias prefix index also powers Redis-backed typeahead. Enter at least three characters of a partial brand, such as `Star`, and the request field offers tenant-filtered matches before a full retrieval run. Selecting a suggestion fills the request; baseline, hybrid, and re-ranked retrieval remain separate stages.

## Local Commands

```bash
make up              # build and start Redis, seed, API, and frontend
make down            # stop containers
make seed            # reset and reseed Redis from the backend container
make test            # run backend and frontend tests
make backend-test    # run pytest
make backend-integration-test # query the seeded Redis Query Engine instance
make frontend-test   # run vitest
make eval            # run golden-query evaluation through the API
```

When another Redis instance already uses port `6379`, start the demo's isolated Docker Redis on a different host port:

```bash
REDIS_PORT=6380 make up
```

## Demo Flow

1. Select `Comparison` mode and search `coffee gift for my child's teacher`.
2. Show baseline lexical, Redis hybrid, and Redis hybrid plus RedisVL re-ranker columns.
3. Search `Best Buy` and expand diagnostics to show exact-match protection.
4. Search `check my balance` to show RedisVL semantic routing to an action card.
5. Change persona from `Anonymous` to `Tech Buyer` for an ambiguous query.
6. Switch tenants to show eligibility and promotion policy changes.
7. Open the evaluation panel and run the golden-query scorecard.
8. Run one re-ranked product search to warm the selected model, then choose concurrency `2` and run the load test. Compare p50/p95 across baseline, hybrid, and re-ranked results; repeat after warmup when the first run included model initialization.

The presenter control includes the same four demo scenes in the UI: relevance comparison, exact-brand trust, action routing, and controlled personalization. Presenter mode hides raw Redis command traces while retaining the ranking explanation, policy evidence, and scorecard.

## Architecture

- `frontend`: React, TypeScript, Vite, lucide-react.
- `backend`: FastAPI, Pydantic, redis-py, RedisVL.
- `redis`: Redis 8.4 local instance.
- `seed`: idempotent backend command that creates indexes and loads data.

Gift-card products use Redis Hashes with the namespace `demo:giftcard:{id}`. The Redis Search physical index is `demo:giftcards:v1`; the API queries the alias `demo:giftcards`. Hash storage is documented in [ADR 0001](docs/decisions/0001-redis-hash-search-index.md).

## API Highlights

- `POST /api/v1/search`: baseline, hybrid, reranked, or comparison search.
- `GET /api/v1/search/suggestions`: tenant-filtered Redis Search typeahead for partial brands and aliases.
- `GET /api/v1/config/public`: personas, tenants, search modes, and demo disclaimers.
- `POST /api/v1/events/click`: records synthetic result clicks.
- `POST /api/v1/evaluations/run`: runs the golden-query evaluator.
- `GET /api/v1/evaluations/{id}`: retrieves a saved scorecard.
- `POST /api/v1/evaluations/load`: runs the bounded concurrent load test.
- `GET /api/v1/telemetry`: returns compact request, route, fallback, and click metrics.
- `GET /health/ready`: checks Redis, index, routing, and model readiness.

## Configuration

See `.env.example` for all supported variables. Defaults run locally with no paid API keys.

Optional Cohere and VoyageAI re-ranker settings are present but disabled unless credentials are supplied. The default provider attempts RedisVL `HFCrossEncoderReranker`; if local model loading fails, the API falls back to hybrid ordering and reports that fallback in diagnostics.

## Troubleshooting

If Redis is not ready:

```bash
docker compose logs redis
docker compose logs seed
docker compose logs api
```

If model downloads are slow, keep the containers running between demos so warmed models and Docker layers are reused.

If you are demonstrating against Redis Cloud or Redis Enterprise, set `REDIS_URL` in `.env`; do not commit secrets or full credential URLs.
