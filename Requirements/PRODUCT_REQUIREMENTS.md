# Product Requirements Document

## 1. Product name

Working title: **GiftFind — RedisVL Relevance Lab**

This is an internal demonstration application. It must include a visible disclaimer that merchant names and synthetic data are for demonstration only and imply no affiliation.

## 2. Product thesis

Gift-card search is not fundamentally a large-corpus problem. It is a relevance, latency, multi-tenancy, and real-time decisioning problem. The demo must prove that Redis can retrieve candidates in milliseconds and that RedisVL can turn those candidates into a composable search pipeline with semantic routing and re-ranking.

The product must make three value propositions visually obvious:

1. **Performance:** Redis dramatically reduces retrieval latency.
2. **Quality:** Hybrid retrieval and re-ranking produce more relevant results than basic lexical search.
3. **Platform value:** Tenant policy, user affinity, promotions, routing, and telemetry can be served from the same real-time Redis foundation.

## 3. Target audience

- Commerce architects evaluating Redis versus OpenSearch.
- Application engineers implementing search and re-ranking.
- Directors responsible for gift-card storefront performance.
- Executives evaluating whether search can become a revenue-producing platform capability.

## 4. Primary personas

### 4.1 Anonymous shopper

Wants a relevant gift quickly. Has no stored profile. Search must work well from query intent alone.

### 4.2 Returning shopper

Has category or brand affinities derived from synthetic past behavior. Personalization may break ties but must not displace an obvious exact match.

### 4.3 Enterprise tenant manager

Represents a bank, retailer, employee-rewards program, or general marketplace. Controls catalog eligibility and bounded promotions.

### 4.4 Search engineer

Needs latency timing, candidate scores, routing decisions, re-ranker output, and final score explainability.

## 5. Core user journeys

### Journey A: Exact brand search

The shopper searches for an exact merchant name such as `Best Buy`.

Expected behavior:

- Exact active brand appears at position 1.
- Fuzzy, semantic, personalized, or promoted products cannot displace the exact match.
- Debug mode explains the exact-match guardrail.

### Journey B: Natural-language discovery

The shopper searches for `coffee gift for my child's teacher`.

Expected behavior:

- Hybrid retrieval finds coffee, cafe, breakfast, and suitable general-purpose cards.
- Re-ranking promotes contextually appropriate gift cards.
- Results are more coherent than baseline lexical search.

### Journey C: Unified engagement search

The shopper enters `check my balance`, `activate my card`, or `where is my order?`.

Expected behavior:

- RedisVL SemanticRouter identifies the intent.
- The UI displays the relevant action card and destination rather than product results.
- Low-confidence routes fall back to product search or a safe help experience.

### Journey D: Personalization

The operator selects a synthetic persona such as `Tech Buyer`, `Coffee Enthusiast`, `Parent`, or `Food Explorer`.

Expected behavior:

- Ambiguous discovery searches change modestly based on affinities.
- Exact brand searches remain stable.
- The score explanation displays the bounded personalization contribution.

### Journey E: Enterprise merchandising

The operator selects a tenant and enables a promotion.

Expected behavior:

- Tenant eligibility filters are applied before ranking.
- A relevant promoted result receives a bounded boost.
- An irrelevant promotion cannot enter or dominate the final results.

### Journey F: Side-by-side proof

The presenter runs a query in comparison mode.

Expected behavior:

- Three result columns appear: `Baseline`, `Redis Hybrid`, and `Redis Hybrid + RedisVL Re-ranker`.
- Each column shows latency and ranked results.
- Changed positions are visually highlighted.
- The re-ranked column can expose score components for each result.

## 6. Functional requirements

### FR-1 Search modes

The system must provide:

- Baseline lexical mode.
- Redis hybrid mode.
- Redis hybrid plus RedisVL re-ranking mode.
- Comparison mode that runs all three with a shared query and filter context.

### FR-2 Search input

The search box must support:

- exact brand names;
- misspellings and partial names;
- category queries;
- natural-language gifting intent;
- support and navigation questions; and
- submission by Enter or button.

### FR-3 Filters

Support tenant, country, currency, delivery type, category, denomination range, and active status. Eligibility filters must execute before vector scoring and re-ranking.

### FR-4 Result cards

Each product result must show:

- merchant name;
- synthetic or placeholder brand image;
- short description;
- category tags;
- delivery types;
- denomination range;
- promotion badge when applicable; and
- optional score explanation in debug mode.

### FR-5 Score explanation

Debug mode must display, where available:

- lexical score or rank;
- vector distance or normalized similarity;
- hybrid/fusion rank;
- re-ranker score;
- exact-match protection;
- personalization boost;
- merchandising boost; and
- final score and rank.

Scores from different models must be normalized before being combined. The UI must label scores as demo diagnostics, not universal probabilities.

### FR-6 Timing explanation

Display timings for:

- intent routing;
- query embedding;
- Redis retrieval;
- re-ranking;
- policy scoring; and
- total server processing.

Client network/render time may be reported separately.

### FR-7 Persona selection

Provide at least five profiles:

- Anonymous
- Tech Buyer
- Coffee Enthusiast
- Parent
- Food Explorer

Profiles must be stored in Redis and loaded by the backend at request time.

### FR-8 Tenant selection

Provide at least three synthetic tenants:

- General Gift Marketplace
- Bank Rewards Portal
- Employee Recognition Store

Each tenant must have a different eligible catalog and at least one optional promotion policy.

### FR-9 Semantic actions

Support at least these routes:

- `product_search`
- `balance_check`
- `card_activation`
- `order_status`
- `customer_support`

### FR-10 Golden-query evaluator

Provide an admin/evaluation page or CLI that executes a version-controlled query set and reports:

- exact-brand Hit@1;
- Mean Reciprocal Rank;
- NDCG@10 when judgments are available;
- Recall@25 for relevant products;
- intent-routing accuracy; and
- latency percentiles.

### FR-11 Event capture

Record synthetic/demo search impressions, result clicks, and selected modes in Redis. Do not collect real personal information.

### FR-12 Seed and reset

Provide idempotent commands to:

- create indexes;
- seed catalog, routes, tenants, profiles, promotions, and judgments;
- regenerate embeddings;
- clear demo events; and
- fully reset local demo state.

## 7. Non-functional requirements

### NFR-1 Performance

After model warm-up on a documented reference environment:

- Redis retrieval p95 target: under 50 ms.
- End-to-end API p95 target: under 500 ms for re-ranked searches.
- Exact thresholds must be configurable for CI and lower-powered developer machines.
- Cold model-loading time must be reported separately and never hidden inside warm latency claims.

### NFR-2 Reliability

- If the re-ranker fails or times out, return Redis hybrid results.
- If vectorization fails, return lexical results.
- If semantic routing confidence is below threshold, fall back safely.
- Failures must be visible in debug metadata and structured logs.

### NFR-3 Explainability

The presenter must be able to explain why results moved. Avoid an opaque single final score with no components.

### NFR-4 Accessibility

The web UI must meet WCAG 2.1 AA basics: keyboard operation, visible focus, semantic labels, sufficient contrast, and non-color-only status indications.

### NFR-5 Portability

- One-command Docker Compose startup.
- Local Redis by default.
- Hosted Redis configured entirely through environment variables.
- No required third-party model API key.

### NFR-6 Security

- No secrets committed to source control.
- Include `.env.example`.
- Validate all request inputs.
- Use restrictive CORS defaults.
- Never log credentials or full connection URLs.

## 8. Success criteria

The demo succeeds when a presenter can show, in under ten minutes:

1. A poor or simplistic baseline result set.
2. Redis hybrid results with materially lower retrieval latency.
3. Re-ranking that visibly improves natural-language relevance.
4. Exact-brand protection.
5. Support-intent routing through the same search box.
6. Tenant and persona changes with bounded ranking effects.
7. An evaluation report quantifying relevance and latency.

## 9. Out of scope

- Payment processing, checkout, issuance, activation backends, or PCI workflows.
- Real authentication or customer identity.
- Real BHN, merchant, or partner data.
- Production recommendation training pipelines.
- Generative answers or an LLM dependency.
- Claims that synthetic conversion or revenue metrics represent actual BHN outcomes.

