# GiftFind Demo Walkthrough

## Preparation

Open `http://localhost:5173` and confirm that the header says Redis connected. The app starts on the Customer search path. Keep Technical details closed until someone asks how a result was produced.

## Opening

GiftFind is a small BHN gift-card discovery experience built to make each RedisVL decision visible. Take one customer request at a time, add one capability, and inspect the improvement before moving on.

The current experience is selected from the BHN demo configuration. Its branding, catalog fixture source, SemanticRouter references, scorecard judgments, Redis key/index names, and five presenter paths are defined independently so a later retailer demo can use its own data and story without copying the application.

## Path 1: Customer search

Select **Customer search**.

1. Click **Run text search**.
   Conventional full-text retrieval is useful, but it mostly rewards literal word overlap.
   Point out the first card and the visible evidence panel.
2. Click **Continue: Add semantic retrieval**, then **Add semantic signal**.
   RedisVL now combines text candidates with vector candidates using reciprocal-rank fusion, adding meaning while retaining exact terms.
   Point out the change statement and the new top-three set.
3. Click **Continue: Re-rank the candidates**, then **Run cross-encoder**.
   Only after Redis has narrowed the field does the cross-encoder compare the complete request with each candidate. This is where a teacher-specific card can rise because it fits the intent, not just the vocabulary.
   Point out the final top result, its visible evidence, and the retrieval timing.
   Choose **TinyBERT L2 (fast)** in the Reranker menu and click **Run selected reranker** to show that Redis retrieval is unchanged while a different RedisVL cross-encoder performs the final ordering.

## Code references

- SemanticRouter: `backend/app/routing/service.py:31`, `backend/app/routing/service.py:94`
- Search-mode dispatch: `backend/app/retrieval/catalog.py:180`, `backend/app/retrieval/catalog.py:204`
- Baseline TextQuery: `backend/app/retrieval/catalog.py:236`, `backend/app/retrieval/catalog.py:442`
- Hybrid text and vector retrieval: `backend/app/retrieval/catalog.py:272`, `backend/app/retrieval/catalog.py:460`
- RRF fusion: `backend/app/retrieval/catalog.py:505`
- Re-ranking pipeline: `backend/app/retrieval/catalog.py:287`, `backend/app/retrieval/catalog.py:568`
- RedisVL cross-encoder call: `backend/app/reranking/provider.py:65`, `backend/app/reranking/provider.py:79`
- Redis prefix typeahead: `backend/app/api/search.py:20`, `backend/app/retrieval/catalog.py:214`, `backend/app/retrieval/catalog.py:474`
- Rendered Redis Search statements: `frontend/src/pages/SearchLabPage.tsx:769`, `frontend/src/pages/SearchLabPage.tsx:809`

## Redis typeahead

Use the **Demo controls** in the presenter panel to enable **Typeahead suggestions**. Type `Star` in the customer request field. Redis Search returns `Starbucks eGift` from the tenant-filtered brand and alias prefix index. Click a suggestion, or highlight it with the arrow keys and press Enter, to fill the request and immediately run the current search step. The active search mode, profile, reranker, and prefix setting stay unchanged. The suggestion lookup is a separate low-latency Redis call; selecting a suggestion then starts the normal search pipeline.

## Short-prefix discovery

Choose **Short-prefix discovery**. The first action searches `Star` as a literal word and shows `AMC Theatres eGift`, where `movie star` is valid catalog text. Continue to the second action. The path turns on **Brand prefix search**, the retrieval trace gains `Brand and alias prefix fill`, and `Starbucks eGift` is protected at the top with visible prefix evidence. This makes the intervention visible without changing the semantic or re-ranking stages.

## Path 2: Exact-brand confidence

Select **Exact-brand confidence**.

1. Click **Find Best Buy**.
   A named brand expresses strong intent. Hybrid retrieval can still find a broad candidate set, but the literal brand remains meaningful.
2. Continue and click **Verify exact match**.
   Re-ranking adds semantic judgment, but the exact-brand guardrail protects the card the customer explicitly requested. Better relevance should not mean less trust.
   Point out the Exact match badge.

## Path 3: Service routing

Select **Service routing**, then click **Route this request**.

Search is not always the right answer. SemanticRouter classifies this as a balance inquiry before product retrieval begins and sends the customer to the useful self-service journey.

Point out that the result is an action, not a product list. Open Technical details only if useful to show that no product retrieval query ran.

## Path 4: Bounded personalization

Select **Bounded personalization**.

1. Click **Search anonymously**.
   This is the neutral answer for a birthday gift for a gamer: the same retrieval and re-ranking pipeline without a customer profile.
2. Continue and click **Apply Tech Buyer profile**.
   Add the declared Tech Buyer preference. Eligible electronics and gaming cards receive a bounded policy contribution, separate from retrieval and inspectable.
   Open Technical details and point out the Persona and Policy contribution fields.

## Golden-query scorecard

Open **Technical details and observability** and click **Run scorecard**.

The scorecard is a compact regression suite, not a live customer search. It sends eight version-controlled requests through baseline, hybrid, and re-ranked retrieval: two exact-brand requests, two discovery requests, and four service-routing requests. Baseline and hybrid stay fixed as controls; the re-ranked row uses the reranker currently selected in the walkthrough. Every run saves the index, embedding model, re-ranker ID and model, candidate count, and top-N setting with the result so an audience can compare like with like.

Read the rows as a quality-and-latency tradeoff, not as a contest with one guaranteed winner:

1. **Hit@1** checks whether the exact brand requested is the first card returned. It applies only to the two exact-brand checks.
2. **MRR** rewards finding the first judged-relevant card earlier in the result list. Higher is better.
3. **NDCG@10** measures the quality of the top ten positions, giving more credit to relevant cards near the top. Higher is better.
4. **Recall@25** checks whether the full set of judged-relevant cards entered the candidate pool. Higher is better.
5. **Route** measures whether product, balance, activation, order-status, and support requests reached the intended journey. Higher is better.
6. **p95** is the slowest meaningful request time in the set. Lower is better; it makes the cost of re-ranking visible.

Run the scorecard once with **MiniLM L6 (balanced)** and once with **TinyBERT L2 (fast)**. Compare only the re-ranked rows, then confirm the model shown beneath each table. The current MiniLM example improves Recall@25 but has a higher p95 latency than hybrid. That means the re-ranker is expanding coverage in this small judgment set, but it is not automatically the best choice for every ranking metric or latency budget. The right conclusion is to validate a model and threshold against agreed business judgments before adopting it.

For a more representative latency check, first run one normal re-ranked request to warm the selected model. Then choose **2** under **Concurrency** and click **Run load test**. This sends the four product judgments through each retrieval mode three times, allowing two requests to overlap. The table reports p50 and p95 for 12 product requests per mode, plus fallbacks and errors. If the first run includes model initialization, repeat it and use the warmed result for the steady-state comparison. A fallback can be a safe low-confidence router decision that continues to product search; errors indicate an actual failed request. Try **4** only after the two-request run; it deliberately adds CPU pressure on a local machine and should be treated as a capacity observation, not a production benchmark.

## Close

The pattern is deliberate: Redis Search finds candidates quickly, RedisVL adds semantic retrieval and re-ranking where it improves the decision, SemanticRouter avoids unnecessary search, and every stage leaves evidence, timing, the underlying query, and a repeatable quality scorecard available for inspection.
