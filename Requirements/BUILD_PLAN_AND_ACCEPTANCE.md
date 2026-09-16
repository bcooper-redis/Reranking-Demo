# Build Plan, Test Plan, and Acceptance Criteria

## 1. Delivery strategy

Build vertical slices. At the end of every milestone, the application must run and tests must pass. Do not postpone integration until the final phase.

## 2. Milestones

### Milestone 0 — Repository and local runtime

Deliver:

- monorepo structure;
- Docker Compose;
- backend and frontend health pages;
- `.env.example`;
- Makefile or equivalent task runner;
- lint, format, and test commands; and
- CI workflow.

Acceptance:

- `docker compose up --build` starts the system.
- Readiness reports Redis connectivity.
- README contains exact setup and troubleshooting commands.

### Milestone 1 — Catalog, indexing, and baseline search

Deliver:

- deterministic data generator;
- Redis JSON/Hash persistence;
- RedisVL index creation;
- idempotent seed/reset commands;
- baseline lexical search API; and
- initial search UI.

Acceptance:

- At least 300 records are indexed.
- Re-running seed does not duplicate records.
- Tenant and eligibility filters work.
- Exact brand and alias test fixtures are searchable.

### Milestone 2 — Hybrid search and comparison UI

Deliver:

- query embedding;
- lexical and vector retrieval;
- native hybrid/RRF or documented fallback;
- exact-match protection;
- score diagnostics; and
- Baseline versus Hybrid comparison.

Acceptance:

- Hybrid mode returns results for natural-language queries with no exact keyword overlap.
- Exact eligible brand ranks first.
- Ineligible tenant products never appear.
- Retrieval stage timings are returned.

### Milestone 3 — RedisVL re-ranking

Deliver:

- required local Hugging Face re-ranker through RedisVL;
- optional provider configuration;
- timeout and hybrid fallback;
- normalized scoring; and
- three-column comparison UI.

Acceptance:

- Re-ranker changes ordering for at least three golden discovery queries.
- Exact brand remains first.
- Forced re-ranker failure returns hybrid results with fallback metadata.
- Warm end-to-end p95 is measured and reported.

### Milestone 4 — Unified intent routing

Deliver:

- RedisVL SemanticRouter;
- action routes and UI cards;
- threshold configuration;
- low-confidence fallback; and
- routing evaluation.

Acceptance:

- All required action intents pass the golden routing tests.
- Product queries reach the product pipeline.
- Unknown queries fail safely.

### Milestone 5 — Personalization and merchandising

Deliver:

- Redis-backed personas and tenant policies;
- bounded profile boosts;
- bounded promotion boosts;
- score explanation; and
- persona/tenant/promotion UI controls.

Acceptance:

- Ambiguous query order changes for at least two personas.
- Exact brand is never displaced.
- Irrelevant promoted products cannot enter the candidate set solely because of promotion.
- Anonymous mode has no personalization boost.

### Milestone 6 — Evaluation, telemetry, and demo polish

Deliver:

- golden-query evaluator;
- MRR, Hit@1, NDCG@10, Recall@25, route accuracy, and latency reporting;
- click-event capture;
- structured logs and metrics;
- responsive/accessibility pass;
- presenter demo mode; and
- screenshots or short GIF in README.

Acceptance:

- One command runs the evaluation suite.
- Results are saved with timestamp, configuration, model names, and index version.
- Presenter can complete the scripted demo in under ten minutes.

## 3. Required automated tests

### Unit tests

- Query normalization and alias matching.
- Exact-match protection.
- RRF implementation if fallback is used.
- Score normalization.
- Boost caps and policy composition.
- Re-ranker timeout fallback.
- Routing threshold behavior.
- Cache-key correctness.

### Integration tests

- Index creation and alias switching against real Redis.
- Seed idempotency.
- Lexical, vector, and hybrid retrieval.
- Tenant pre-filtering.
- RedisVL local re-ranker integration.
- SemanticRouter integration.
- API schemas and failure responses.

### End-to-end tests

- Search from landing page.
- Switch modes and compare results.
- Change persona and tenant.
- Run an action query such as `check my balance`.
- Expand score diagnostics.
- Display graceful Redis or re-ranker failure states through controlled test doubles.

### Load tests

Define warm-model scenarios for:

- baseline searches;
- hybrid searches;
- re-ranked searches;
- mixed anonymous and personalized traffic; and
- burst traffic representative of a holiday peak.

Record p50, p95, p99, throughput, errors, and fallback rate. Do not claim production capacity from a laptop test.

## 4. Golden query set

Include at least 40 judged queries. Minimum categories:

| Category | Examples | Expected assertion |
|---|---|---|
| Exact brand | `Best Buy`, `H-E-B` | Eligible exact brand Hit@1 |
| Alias | `bestbuy`, brand abbreviation | Correct brand in top 1–3 |
| Typo | `Starbuks`, `restarant card` | Intended category/brand near top |
| Recipient | `gift for a gamer` | Gaming/electronics dominate top 10 |
| Occasion | `last-minute birthday gift` | eGift and birthday-suitable results |
| Budget | `dinner gift under $75` | Food results satisfying denomination constraint |
| Intent | `check my balance` | `balance_check` route |
| Intent | `activate this card` | `card_activation` route |
| Intent | `where is my order` | `order_status` route |
| Safety | unknown or nonsense query | Safe fallback and no fabricated answer |

Each judgment record should include query, tenant, filters, expected route, relevant IDs or categories, exact-match expectation, and optional graded relevance values.

## 5. Quality gates

No milestone is complete unless:

- lint and type checks pass;
- required automated tests pass;
- no required feature contains a placeholder or TODO;
- the README reflects current commands;
- configuration defaults are documented;
- failures degrade to the specified fallback; and
- diagnostics identify the active models and index version.

## 6. Demonstration script

### Scene 1 — The baseline problem

Select Anonymous and General Marketplace. Search `coffee gift for my child's teacher` in comparison mode. Briefly show that baseline lexical ordering is less coherent.

### Scene 2 — Redis hybrid retrieval

Highlight Redis retrieval latency, lexical/vector candidates, and improved recall.

### Scene 3 — RedisVL re-ranking

Show how the cross-encoder changes the top results. Expand one result to show the re-ranker score and stage timing.

### Scene 4 — Exact-match trust

Search `Best Buy`. Show exact match at position 1 even when a different merchant is promoted.

### Scene 5 — One search box, multiple journeys

Search `check my balance`. Show SemanticRouter selecting the balance action without calling an LLM.

### Scene 6 — Platform reuse

Switch between General Marketplace, Bank Rewards, and Employee Recognition tenants. Show eligibility and promotion changes without changing application code.

### Scene 7 — Controlled personalization

Run an ambiguous query under Anonymous and Tech Buyer. Show a modest ranking change and the capped boost.

### Scene 8 — Scorecard

Open the evaluation report. Compare baseline, hybrid, and re-ranked quality plus p95 latency.

Close with: Redis is the real-time serving layer, RedisVL is the composable relevance framework, and model choice remains open.

## 7. Definition of done

The project is done when a new developer can clone it, configure no paid credentials, run one startup command, seed the data, open the UI, execute the entire demonstration script, and run all tests and evaluations using documented commands.

