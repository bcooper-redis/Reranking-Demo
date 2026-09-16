import { useEffect, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";

import { getReadiness, type Readiness } from "../api/health";
import {
  getPublicConfig,
  getSearchSuggestions,
  getTelemetry,
  runEvaluation,
  runLoadTest,
  searchCatalog,
  type ComparisonResponse,
  type EvaluationRun,
  type LoadTestRun,
  type PublicConfig,
  type SearchMode,
  type SearchResponse,
  type SearchSuggestion,
  type TelemetrySnapshot,
} from "../api/search";

type PageState =
  | { kind: "loading" }
  | { kind: "ready"; config: PublicConfig; readiness: Readiness }
  | { kind: "error" };

type DemoStep = {
  title: string;
  actionLabel: string;
  detail: string;
  narration: string;
  mode: Exclude<SearchMode, "compare">;
  profileId: string;
  promotionId: string | null;
};

type DemoPath = {
  id: string;
  label: string;
  summary: string;
  query: string;
  steps: DemoStep[];
};

const DEMO_PATHS: DemoPath[] = [
  {
    id: "teacher-relevance",
    label: "Teacher appreciation",
    summary:
      "Show why text, semantic retrieval, and re-ranking produce different answers.",
    query: "coffee gift for my child's teacher",
    steps: [
      {
        title: "Start with text retrieval",
        actionLabel: "Run text search",
        detail: "Text retrieval favors literal coffee and teacher terms.",
        narration:
          "We begin with the familiar search pattern: match the words the customer typed.",
        mode: "baseline",
        profileId: "anonymous",
        promotionId: null,
      },
      {
        title: "Add semantic retrieval",
        actionLabel: "Add semantic signal",
        detail:
          "Redis combines text and vector candidates using reciprocal-rank fusion.",
        narration:
          "Now RedisVL understands related meaning, so a thoughtful teacher gift can compete even when it shares fewer words.",
        mode: "hybrid",
        profileId: "anonymous",
        promotionId: null,
      },
      {
        title: "Re-rank the candidates",
        actionLabel: "Run cross-encoder",
        detail:
          "The cross-encoder reads the full request against each hybrid candidate before choosing the final order.",
        narration:
          "Only after Redis has found a tight candidate set do we spend the extra work to judge the whole request against each card.",
        mode: "reranked",
        profileId: "anonymous",
        promotionId: null,
      },
    ],
  },
  {
    id: "exact-brand",
    label: "Exact-brand confidence",
    summary:
      "Show that a precise brand request remains protected while the retrieval stack gets smarter.",
    query: "Best Buy",
    steps: [
      {
        title: "Retrieve brand candidates",
        actionLabel: "Find Best Buy",
        detail:
          "Hybrid retrieval brings together literal brand matches and related gift-card candidates.",
        narration:
          "For an explicit brand request, relevance starts with honoring the brand the customer actually named.",
        mode: "hybrid",
        profileId: "anonymous",
        promotionId: null,
      },
      {
        title: "Verify the final ranking",
        actionLabel: "Verify exact match",
        detail:
          "Re-ranking uses the full request while the exact-brand guardrail keeps the named brand prominent.",
        narration:
          "The re-ranker adds nuance without losing trust: an exact brand request should not be displaced by a merely similar card.",
        mode: "reranked",
        profileId: "anonymous",
        promotionId: null,
      },
    ],
  },
  {
    id: "service-routing",
    label: "Service routing",
    summary:
      "Show SemanticRouter sending an operational request to the right action instead of product search.",
    query: "check my balance",
    steps: [
      {
        title: "Classify the request",
        actionLabel: "Route this request",
        detail:
          "SemanticRouter recognizes a balance inquiry and returns the correct self-service journey without catalog retrieval.",
        narration:
          "Not every customer request is a product search. RedisVL classifies the intent first, then routes directly to the useful action.",
        mode: "baseline",
        profileId: "anonymous",
        promotionId: null,
      },
    ],
  },
  {
    id: "personalization",
    label: "Bounded personalization",
    summary:
      "Show a transparent profile signal moving eligible electronics cards without changing retrieval itself.",
    query: "a birthday gift for a gamer",
    steps: [
      {
        title: "Search without a profile",
        actionLabel: "Search anonymously",
        detail:
          "The re-ranker orders results only from the customer request and catalog evidence, without a profile preference.",
        narration:
          "First, this is the neutral answer: same retrieval and re-ranking pipeline, no profile signal applied.",
        mode: "reranked",
        profileId: "anonymous",
        promotionId: null,
      },
      {
        title: "Apply a declared profile",
        actionLabel: "Apply Tech Buyer profile",
        detail:
          "Eligible electronics and gaming cards receive a bounded +0.09 policy contribution; the result evidence and technical details remain visible.",
        narration:
          "Now we add one declared preference, not a black box. The audience can see that policy signal and its contribution separately.",
        mode: "reranked",
        profileId: "tech_buyer",
        promotionId: null,
      },
    ],
  },
];

function ResultList({
  response,
  comparisonSource,
  comparisonLabel,
  compact = false,
  visibleLimit,
  onResultClick,
}: {
  response: SearchResponse;
  comparisonSource?: SearchResponse;
  comparisonLabel?: string;
  compact?: boolean;
  visibleLimit?: number;
  onResultClick?: (response: SearchResponse, resultId: string) => void;
}) {
  const comparisonRanks = new Map(
    comparisonSource?.results.map((result, index) => [result.id, index + 1]),
  );
  const displayedResults = compact
    ? response.results.slice(0, visibleLimit ?? 5)
    : response.results;
  return (
    <section className="results" aria-label={`${response.mode} search results`}>
      <div className="results-heading">
        <p>
          {compact ? `Top ${displayedResults.length} of ` : ""}
          {response.results.length} results
        </p>
        <p>
          {response.timings_ms.retrieval?.toFixed(2) ?? "-"} ms Redis retrieval
        </p>
      </div>
      <ol className={compact ? "compact-results" : undefined}>
        {displayedResults.map((result, index) => {
          const previousRank = comparisonRanks.get(result.id);
          return (
            <li key={result.id}>
              <div>
                <div className="brand-line">
                  <span className="rank">{index + 1}</span>
                  <h3>{result.brand_name}</h3>
                  {result.score_breakdown?.exact_match && (
                    <span className="guardrail">Exact match</span>
                  )}
                  {result.score_breakdown?.prefix_match &&
                    !result.score_breakdown.exact_match && (
                      <span className="guardrail">Brand prefix</span>
                    )}
                </div>
                <p className="result-description">{result.description}</p>
                <div className="tags">
                  {result.categories.map((category) => (
                    <span key={category}>{category}</span>
                  ))}
                  {result.promoted && (
                    <span className="promotion-badge">Promoted</span>
                  )}
                </div>
                {previousRank && previousRank !== index + 1 && (
                  <p className="rank-change">
                    Moved from {comparisonLabel ?? "the prior stage"} #
                    {previousRank}
                  </p>
                )}
              </div>
              <div className="result-meta">
                <span>
                  ${result.min_denomination}-${result.max_denomination}
                </span>
                <span>{result.delivery_types.join(", ")}</span>
                {onResultClick && !compact && (
                  <button
                    className="result-select"
                    onClick={() => onResultClick(response, result.id)}
                    type="button"
                  >
                    Select
                  </button>
                )}
              </div>
            </li>
          );
        })}
      </ol>
      {response.fallbacks.length > 0 && (
        <p className="fallback">Fallback: {response.fallbacks.join(", ")}</p>
      )}
    </section>
  );
}

function StepInsight({
  response,
  previousResponse,
  detail,
}: {
  response: SearchResponse;
  previousResponse: SearchResponse | null;
  detail: string;
}) {
  if (response.action) {
    return (
      <section className="step-insight" aria-live="polite">
        <p className="label">What changed</p>
        <h3>Product retrieval was skipped</h3>
        <p>{detail}</p>
      </section>
    );
  }

  const winner = response.results[0];
  const priorWinner = previousResponse?.results[0];
  const matchingFields = winner?.score_breakdown?.matching_fields?.join(", ");
  const headline =
    priorWinner && winner && priorWinner.id !== winner.id
      ? `#1 changed from ${priorWinner.brand_name} to ${winner.brand_name}`
      : winner
        ? `${winner.brand_name} holds the top position`
        : "The current stage returned no product results";

  return (
    <section className="step-insight" aria-live="polite">
      <p className="label">What changed</p>
      <h3>{headline}</h3>
      <p>{detail}</p>
      {matchingFields && (
        <p className="signal-line">
          <strong>Visible evidence:</strong> {matchingFields}
        </p>
      )}
    </section>
  );
}

type FlowStep = {
  title: string;
  detail: string;
};

function formatTiming(value: number | undefined): string {
  return value === undefined ? "" : ` (${value.toFixed(2)} ms)`;
}

function routeDetail(response: SearchResponse): string {
  const intent = response.intent;
  if (!intent) return "Waiting for a route decision.";
  if (intent.fallback) {
    return `No confident route was available, so ${intent.name.replaceAll("_", " ")} continued as the safe fallback (${intent.source.replaceAll("_", " ")}).`;
  }
  if (intent.distance === null || intent.threshold === null) {
    return `${intent.name.replaceAll("_", " ")} was selected by ${intent.source.replaceAll("_", " ")}.`;
  }
  const routeOutcome = response.action
    ? "Product retrieval stopped and the configured action journey was returned."
    : "The product-search path continued.";
  return `${intent.name.replaceAll("_", " ")} won because distance ${intent.distance.toFixed(3)} met the ${intent.threshold.toFixed(3)} threshold. ${routeOutcome}`;
}

function executionSteps(
  search: SearchResponse | ComparisonResponse | null,
  selectedMode: SearchMode,
): FlowStep[] {
  if (!search) {
    return [
      {
        title: "1. RedisVL SemanticRouter",
        detail:
          "Classify the query before choosing an action or product-search path.",
      },
      {
        title: "2. Selected retrieval path",
        detail:
          "Run the calls for the chosen mode only after product search is selected.",
      },
    ];
  }

  const routeResponse =
    search.mode === "compare" ? search.comparisons.baseline : search;
  const routeStep: FlowStep = {
    title: "1. RedisVL SemanticRouter",
    detail: `${routeDetail(routeResponse)}${formatTiming(routeResponse.timings_ms.routing)}`,
  };

  if (routeResponse.action) return [routeStep];

  if (search.mode === "compare") {
    const { baseline, hybrid, reranked } = search.comparisons;
    return [
      routeStep,
      {
        title: "2. Baseline: RedisVL TextQuery",
        detail: `FT.SEARCH full-text retrieval completed${formatTiming(baseline.timings_ms.retrieval)}.`,
      },
      {
        title: "3. Hybrid: text + embedding + VectorQuery",
        detail: `RedisVL retrieved lexical and vector candidates, fused them with RRF, then applied the exact-match guardrail${formatTiming(hybrid.timings_ms.retrieval)}.`,
      },
      {
        title: "4. Re-ranked: fresh hybrid candidate set",
        detail: `The re-rank branch runs its own hybrid retrieval before scoring candidates${formatTiming(reranked.timings_ms.retrieval)}.`,
      },
      {
        title: "5. RedisVL HFCrossEncoderReranker.rank",
        detail: `The cross-encoder scored that candidate set after retrieval${formatTiming(reranked.timings_ms.reranking)}.`,
      },
    ];
  }

  if (selectedMode === "baseline") {
    return [
      routeStep,
      {
        title: "2. RedisVL TextQuery",
        detail: `FT.SEARCH full-text retrieval completed${formatTiming(routeResponse.timings_ms.retrieval)}.`,
      },
    ];
  }

  const hybridStep: FlowStep = {
    title: "2. RedisVL text + embedding + VectorQuery",
    detail: `Lexical and vector candidates were fused with RRF, then exact brand and alias matches were protected${formatTiming(routeResponse.timings_ms.retrieval)}.`,
  };
  if (selectedMode === "hybrid") return [routeStep, hybridStep];

  return [
    routeStep,
    hybridStep,
    {
      title: "3. RedisVL HFCrossEncoderReranker.rank",
      detail: `The reranker scored the hybrid candidate set after retrieval${formatTiming(routeResponse.timings_ms.reranking)}.`,
    },
  ];
}

function TimingPanel({
  search,
  roundTripMs,
}: {
  search: SearchResponse | ComparisonResponse | null;
  roundTripMs: number | null;
}) {
  if (!search || roundTripMs === null) {
    return (
      <p className="timing-empty">Timing appears after the first search.</p>
    );
  }

  const actionResponse = search.mode !== "compare" ? search.action : null;
  const actionRoutingMs =
    search.mode !== "compare" ? search.timings_ms.routing : undefined;
  const lookupLabel = actionResponse ? "Router lookup" : "Redis lookup";
  const lookupTiming = actionResponse
    ? `SemanticRouter ${actionRoutingMs?.toFixed(2) ?? "-"} ms`
    : search.mode === "compare"
      ? `Baseline ${search.comparisons.baseline.timings_ms.retrieval?.toFixed(2) ?? "-"} ms; Hybrid ${search.comparisons.hybrid.timings_ms.retrieval?.toFixed(2) ?? "-"} ms; Re-ranked ${search.comparisons.reranked.timings_ms.reranking?.toFixed(2) ?? "-"} ms`
      : `${search.timings_ms.retrieval?.toFixed(2) ?? "-"} ms`;
  const warmP95 =
    search.mode === "compare"
      ? search.comparisons.reranked.diagnostics?.warm_p95_ms
      : search.diagnostics?.warm_p95_ms;

  return (
    <dl className="timing-list">
      <div>
        <dt>{lookupLabel}</dt>
        <dd>{lookupTiming}</dd>
      </div>
      <div>
        <dt>Total round trip</dt>
        <dd>{roundTripMs.toFixed(2)} ms</dd>
      </div>
      {typeof warmP95 === "number" && (
        <div>
          <dt>Warm re-rank p95</dt>
          <dd>{warmP95.toFixed(2)} ms</dd>
        </div>
      )}
    </dl>
  );
}

function RoutingPanel({
  search,
}: {
  search: SearchResponse | ComparisonResponse | null;
}) {
  const intent =
    search?.mode === "compare"
      ? search.comparisons.baseline.intent
      : search?.intent;

  if (!intent) {
    return (
      <p className="timing-empty">
        Route selection appears after the first search.
      </p>
    );
  }

  return (
    <dl className="routing-list">
      <div>
        <dt>Intent</dt>
        <dd>{intent.name.replaceAll("_", " ")}</dd>
      </div>
      <div>
        <dt>Confidence</dt>
        <dd>{intent.confidence.toFixed(2)}</dd>
      </div>
      <div>
        <dt>Distance / threshold</dt>
        <dd>
          {intent.distance?.toFixed(3) ?? "-"} /{" "}
          {intent.threshold?.toFixed(3) ?? "-"}
        </dd>
      </div>
      <div>
        <dt>Decision source</dt>
        <dd>{intent.source.replaceAll("_", " ")}</dd>
      </div>
    </dl>
  );
}

function PolicyPanel({
  search,
  profileName,
  promotionName,
}: {
  search: SearchResponse | ComparisonResponse | null;
  profileName: string;
  promotionName: string;
}) {
  const response =
    search?.mode === "compare" ? search.comparisons.reranked : search;
  const promotedCount =
    response?.results.filter((result) => result.promoted).length ?? 0;

  if (!response || response.action) {
    return (
      <p className="timing-empty">
        Policy contribution appears after a product search.
      </p>
    );
  }

  return (
    <dl className="routing-list">
      <div>
        <dt>Persona</dt>
        <dd>{profileName}</dd>
      </div>
      <div>
        <dt>Promotion</dt>
        <dd>{promotionName}</dd>
      </div>
      <div>
        <dt>Eligible promoted results</dt>
        <dd>{promotedCount}</dd>
      </div>
      <div>
        <dt>Policy scoring</dt>
        <dd>{response.timings_ms.policy?.toFixed(2) ?? "-"} ms</dd>
      </div>
    </dl>
  );
}

function RerankerPanel({ search }: { search: SearchResponse | null }) {
  const diagnostics = search?.mode === "reranked" ? search.diagnostics : null;

  if (!diagnostics) {
    return (
      <p className="timing-empty">
        Model details appear after a re-ranked search.
      </p>
    );
  }

  return (
    <dl className="routing-list">
      <div>
        <dt>Provider</dt>
        <dd>{diagnostics.reranker_provider ?? "-"}</dd>
      </div>
      <div>
        <dt>Selected model</dt>
        <dd>{diagnostics.reranker_model ?? "-"}</dd>
      </div>
      <div>
        <dt>Candidate limit</dt>
        <dd>{diagnostics.rerank_top_n ?? "-"}</dd>
      </div>
    </dl>
  );
}

function ScorecardPanel({
  evaluation,
  isRunning,
  isAvailable,
  onRun,
  loadTest,
  isLoadRunning,
  loadConcurrency,
  onLoadConcurrencyChange,
  onRunLoad,
  rerankerName,
}: {
  evaluation: EvaluationRun | null;
  isRunning: boolean;
  isAvailable: boolean;
  onRun: () => void;
  loadTest: LoadTestRun | null;
  isLoadRunning: boolean;
  loadConcurrency: number;
  onLoadConcurrencyChange: (concurrency: number) => void;
  onRunLoad: () => void;
  rerankerName: string;
}) {
  return (
    <section className="scorecard-panel" aria-labelledby="scorecard-heading">
      <div className="scorecard-heading">
        <div>
          <p className="label">Evaluation</p>
          <h2 id="scorecard-heading">Golden-query scorecard</h2>
        </div>
        <div className="scorecard-actions">
          <button
            disabled={isRunning || isLoadRunning || !isAvailable}
            onClick={onRun}
            type="button"
          >
            {isRunning ? "Running scorecard" : "Run scorecard"}
          </button>
          <label className="load-control">
            <span>Concurrency</span>
            <select
              disabled={isRunning || isLoadRunning || !isAvailable}
              onChange={(event) =>
                onLoadConcurrencyChange(Number(event.target.value))
              }
              value={loadConcurrency}
            >
              {[1, 2, 4].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <button
            disabled={isRunning || isLoadRunning || !isAvailable}
            onClick={onRunLoad}
            type="button"
          >
            {isLoadRunning ? "Applying load" : "Run load test"}
          </button>
        </div>
      </div>
      {!evaluation && (
        <p className="timing-empty">
          Baseline and hybrid are controls; the re-ranked row uses{" "}
          {rerankerName}. Results are saved with the active index and model
          configuration.
        </p>
      )}
      {evaluation && (
        <>
          <div className="scorecard-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Mode</th>
                  <th>Hit@1</th>
                  <th>MRR</th>
                  <th>NDCG@10</th>
                  <th>Recall@25</th>
                  <th>Route</th>
                  <th>p95</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(evaluation.metrics).map(([mode, metric]) => (
                  <tr key={mode}>
                    <th>{mode}</th>
                    <td>{metric.exact_brand_hit_at_1.toFixed(2)}</td>
                    <td>{metric.mrr.toFixed(2)}</td>
                    <td>{metric.ndcg_at_10.toFixed(2)}</td>
                    <td>{metric.recall_at_25.toFixed(2)}</td>
                    <td>{metric.route_accuracy.toFixed(2)}</td>
                    <td>{metric.latency_p95_ms.toFixed(0)} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="scorecard-meta">
            {evaluation.configuration.embedding_model} ·{" "}
            {evaluation.configuration.reranker_model}· index{" "}
            {evaluation.configuration.index_version}
          </p>
        </>
      )}
      {loadTest && (
        <section
          className="load-results"
          aria-labelledby="load-results-heading"
        >
          <div>
            <p className="label">Concurrent product load</p>
            <h3 id="load-results-heading">
              {loadTest.concurrency} concurrent requests · {loadTest.rounds}{" "}
              rounds
            </h3>
          </div>
          <div className="scorecard-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Mode</th>
                  <th>Requests</th>
                  <th>p50</th>
                  <th>p95</th>
                  <th>Fallbacks</th>
                  <th>Errors</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(loadTest.metrics).map(([mode, metric]) => (
                  <tr key={mode}>
                    <th>{mode}</th>
                    <td>{metric.request_count}</td>
                    <td>{metric.latency_p50_ms.toFixed(0)} ms</td>
                    <td>{metric.latency_p95_ms.toFixed(0)} ms</td>
                    <td>{metric.fallback_count}</td>
                    <td>{metric.error_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="scorecard-meta">
            {loadTest.configuration.reranker_model} · product-only workload
          </p>
        </section>
      )}
    </section>
  );
}

function TelemetryPanel({
  telemetry,
}: {
  telemetry: TelemetrySnapshot | null;
}) {
  if (!telemetry) {
    return (
      <p className="timing-empty">Telemetry appears after the first request.</p>
    );
  }
  return (
    <dl className="routing-list">
      <div>
        <dt>Requests / clicks</dt>
        <dd>
          {telemetry.request_count} / {telemetry.click_count}
        </dd>
      </div>
      <div>
        <dt>Request p95</dt>
        <dd>{telemetry.latency_p95_ms.toFixed(2)} ms</dd>
      </div>
      <div>
        <dt>Fallbacks</dt>
        <dd>{telemetry.fallback_count}</dd>
      </div>
    </dl>
  );
}

function ActionRouteCard({ response }: { response: SearchResponse }) {
  if (!response.action || !response.intent) return null;

  return (
    <section
      className="action-card"
      aria-label={`${response.action.title} action`}
    >
      <p className="label">SemanticRouter action</p>
      <h3>{response.action.title}</h3>
      <p>{response.action.description}</p>
      <p className="action-destination">{response.action.destination_label}</p>
    </section>
  );
}

function RedisQueryPanel({
  search,
}: {
  search: SearchResponse | ComparisonResponse | null;
}) {
  if (!search) {
    return (
      <p className="timing-empty">Queries appear after the first search.</p>
    );
  }

  const searches =
    search.mode === "compare"
      ? [
          { label: "Baseline lexical", response: search.comparisons.baseline },
          { label: "Redis hybrid", response: search.comparisons.hybrid },
          { label: "RedisVL re-ranked", response: search.comparisons.reranked },
        ]
      : [{ label: search.mode, response: search }];

  if (
    searches.every(({ response }) => response.redis_search_queries.length === 0)
  ) {
    return (
      <p className="timing-empty">
        No product retrieval ran for this routed action.
      </p>
    );
  }

  return (
    <div className="redis-query-list">
      {searches.map(({ label, response }) => (
        <details key={label} open={searches.length === 1}>
          <summary>
            {label} ({response.redis_search_queries.length})
          </summary>
          {response.redis_search_queries.map((redisQuery) => (
            <div className="redis-query" key={redisQuery.label}>
              <p>{redisQuery.label}</p>
              <code>{redisQuery.statement}</code>
              {redisQuery.parameters.map((parameter) => (
                <span key={parameter}>{parameter}</span>
              ))}
            </div>
          ))}
        </details>
      ))}
    </div>
  );
}

export function SearchLabPage() {
  const [page, setPage] = useState<PageState>({ kind: "loading" });
  const tenantId = "general";
  const [pathId, setPathId] = useState(DEMO_PATHS[0].id);
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [query, setQuery] = useState(DEMO_PATHS[0].query);
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [isSuggestionOpen, setIsSuggestionOpen] = useState(false);
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(-1);
  const [rerankerId, setRerankerId] = useState("minilm_l6");
  const [journey, setJourney] = useState<SearchResponse[]>([]);
  const [search, setSearch] = useState<SearchResponse | null>(null);
  const [searchError, setSearchError] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [roundTripMs, setRoundTripMs] = useState<number | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationRun | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [loadTest, setLoadTest] = useState<LoadTestRun | null>(null);
  const [isLoadTesting, setIsLoadTesting] = useState(false);
  const [loadConcurrency, setLoadConcurrency] = useState(2);
  const [telemetry, setTelemetry] = useState<TelemetrySnapshot | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      getReadiness(controller.signal),
      getPublicConfig(controller.signal),
    ])
      .then(([readiness, config]) =>
        setPage({ kind: "ready", readiness, config }),
      )
      .catch(() => setPage({ kind: "error" }));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const normalizedQuery = query.trim();
    if (
      normalizedQuery.length < 3 ||
      normalizedQuery.length > 40 ||
      normalizedQuery.split(/\s+/).length > 3
    ) {
      setSuggestions([]);
      setActiveSuggestionIndex(-1);
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void getSearchSuggestions(query, tenantId, controller.signal)
        .then((response) => {
          setSuggestions(response.suggestions);
          setActiveSuggestionIndex(-1);
        })
        .catch(() => {
          if (!controller.signal.aborted) setSuggestions([]);
        });
    }, 180);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [query, tenantId]);

  const config = page.kind === "ready" ? page.config : null;
  const activePath =
    DEMO_PATHS.find((candidate) => candidate.id === pathId) ?? DEMO_PATHS[0];
  const activeStep = activePath.steps[activeStepIndex];
  const activeResponse = journey[activeStepIndex] ?? null;
  const previousResponse =
    activeStepIndex > 0 ? (journey[activeStepIndex - 1] ?? null) : null;
  const profileName =
    config?.profiles.find((profile) => profile.id === activeStep.profileId)
      ?.display_name ?? "Anonymous";
  const promotionName = activeStep.promotionId
    ? (config?.promotions.find(
        (promotion) => promotion.id === activeStep.promotionId,
      )?.display_name ?? "None")
    : "None";
  const rerankerName =
    config?.rerankers.find((reranker) => reranker.id === rerankerId)
      ?.display_name ?? "selected reranker";

  async function runStep(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!query.trim()) return;
    setIsSearching(true);
    setSearchError(false);
    setRoundTripMs(null);
    setIsSuggestionOpen(false);
    const requestStartedAt = performance.now();
    try {
      const response = await searchCatalog(
        query,
        tenantId,
        activeStep.profileId,
        activeStep.promotionId,
        activeStep.mode,
        rerankerId,
      );
      if (response.mode === "compare") throw new Error("Unexpected comparison");
      setSearch(response);
      setJourney((current) => [...current.slice(0, activeStepIndex), response]);
      setRoundTripMs(performance.now() - requestStartedAt);
      void refreshTelemetry();
    } catch {
      setSearchError(true);
    } finally {
      setIsSearching(false);
    }
  }

  async function refreshTelemetry() {
    try {
      setTelemetry(await getTelemetry());
    } catch {
      // Search results remain useful if presentation telemetry is unavailable.
    }
  }

  async function handleRunEvaluation() {
    setIsEvaluating(true);
    try {
      setEvaluation(await runEvaluation(rerankerId));
      void refreshTelemetry();
    } finally {
      setIsEvaluating(false);
    }
  }

  async function handleRunLoadTest() {
    setIsLoadTesting(true);
    try {
      setLoadTest(await runLoadTest(rerankerId, loadConcurrency));
      void refreshTelemetry();
    } finally {
      setIsLoadTesting(false);
    }
  }

  function choosePath(nextPathId: string) {
    const nextPath =
      DEMO_PATHS.find((candidate) => candidate.id === nextPathId) ??
      DEMO_PATHS[0];
    setPathId(nextPath.id);
    setQuery(nextPath.query);
    setSuggestions([]);
    setIsSuggestionOpen(false);
    setActiveSuggestionIndex(-1);
    setActiveStepIndex(0);
    setJourney([]);
    setSearch(null);
    setRoundTripMs(null);
    setSearchError(false);
  }

  function restartPath() {
    setQuery(activePath.query);
    setSuggestions([]);
    setIsSuggestionOpen(false);
    setActiveSuggestionIndex(-1);
    setActiveStepIndex(0);
    setJourney([]);
    setSearch(null);
    setRoundTripMs(null);
    setSearchError(false);
  }

  function selectSuggestion(suggestion: SearchSuggestion) {
    setQuery(suggestion.brand_name);
    setSuggestions([]);
    setIsSuggestionOpen(false);
    setActiveSuggestionIndex(-1);
  }

  function handleSuggestionKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!isSuggestionOpen || suggestions.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveSuggestionIndex((index) =>
        Math.min(index + 1, suggestions.length - 1),
      );
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveSuggestionIndex((index) => Math.max(index - 1, 0));
    } else if (event.key === "Escape") {
      setIsSuggestionOpen(false);
      setActiveSuggestionIndex(-1);
    } else if (event.key === "Enter" && activeSuggestionIndex >= 0) {
      event.preventDefault();
      selectSuggestion(suggestions[activeSuggestionIndex]);
    }
  }

  const isReady = page.kind === "ready" && page.readiness.redis === "connected";
  const flowSteps = executionSteps(activeResponse, activeStep.mode);
  const hasNextStep = activeStepIndex < activePath.steps.length - 1;

  return (
    <main className="search-page">
      <header className="masthead">
        <p className="eyebrow">Blackhawk Networks demo</p>
        <div className="title-row">
          <div>
            <h1>GiftFind</h1>
            <p className="subtitle">RedisVL Relevance Lab</p>
          </div>
          <p
            className={
              isReady ? "runtime-state healthy" : "runtime-state unavailable"
            }
            aria-live="polite"
          >
            {isReady ? "Redis connected" : "Checking runtime"}
          </p>
        </div>
      </header>
      <section className="search-workspace" aria-labelledby="search-heading">
        <div className="workspace-heading">
          <div>
            <p className="label">RedisVL demo</p>
            <h2 id="search-heading">Guided relevance walkthrough</h2>
          </div>
          <p>
            {config
              ? `${config.catalog_count} catalog cards indexed`
              : "Loading catalog"}
          </p>
        </div>
        <div className="walkthrough-shell">
          <aside className="path-picker" aria-labelledby="path-picker-heading">
            <p className="label">Choose a path</p>
            <h3 id="path-picker-heading">Demo storyline</h3>
            <label>
              <span>Path</span>
              <select
                onChange={(event) => choosePath(event.target.value)}
                value={pathId}
              >
                {DEMO_PATHS.map((path) => (
                  <option key={path.id} value={path.id}>
                    {path.label}
                  </option>
                ))}
              </select>
            </label>
            <p>{activePath.summary}</p>
          </aside>
          <section
            className="walkthrough-stage"
            aria-labelledby="stage-heading"
          >
            <p className="label">
              Step {activeStepIndex + 1} of {activePath.steps.length}
            </p>
            <h3 id="stage-heading">{activeStep.title}</h3>
            <ol className="walkthrough-steps" aria-label="Demo steps">
              {activePath.steps.map((step, index) => (
                <li
                  className={
                    index === activeStepIndex
                      ? "current"
                      : index < activeStepIndex
                        ? "complete"
                        : ""
                  }
                  key={step.title}
                >
                  <span>{index + 1}</span>
                  {step.title}
                </li>
              ))}
            </ol>
            <form className="walkthrough-action" onSubmit={runStep}>
              <label className="walkthrough-query">
                <span>Customer request</span>
                <div className="autocomplete">
                  <input
                    aria-autocomplete="list"
                    aria-controls="redis-suggestions"
                    aria-expanded={isSuggestionOpen && suggestions.length > 0}
                    onChange={(event) => {
                      setQuery(event.target.value);
                      setIsSuggestionOpen(true);
                      setActiveSuggestionIndex(-1);
                    }}
                    onFocus={() => setIsSuggestionOpen(true)}
                    onKeyDown={handleSuggestionKeyDown}
                    value={query}
                  />
                  {isSuggestionOpen && suggestions.length > 0 && (
                    <div
                      className="autocomplete-menu"
                      id="redis-suggestions"
                      role="listbox"
                    >
                      <p>Redis Search suggestions</p>
                      {suggestions.map((suggestion, index) => (
                        <button
                          aria-selected={index === activeSuggestionIndex}
                          className={
                            index === activeSuggestionIndex ? "active" : ""
                          }
                          key={suggestion.id}
                          onClick={() => selectSuggestion(suggestion)}
                          role="option"
                          type="button"
                        >
                          {suggestion.brand_name}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </label>
              {activeStep.mode === "reranked" && (
                <label className="reranker-field">
                  <span>Reranker</span>
                  <select
                    onChange={(event) => setRerankerId(event.target.value)}
                    value={rerankerId}
                  >
                    {config?.rerankers.map((reranker) => (
                      <option key={reranker.id} value={reranker.id}>
                        {reranker.display_name}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {!activeResponse && (
                <button disabled={isSearching || !isReady} type="submit">
                  {isSearching ? "Working" : activeStep.actionLabel}
                </button>
              )}
              {activeResponse && activeStep.mode === "reranked" && (
                <button disabled={isSearching || !isReady} type="submit">
                  {isSearching ? "Working" : "Run selected reranker"}
                </button>
              )}
              {activeResponse && hasNextStep && (
                <button
                  onClick={() => setActiveStepIndex((index) => index + 1)}
                  type="button"
                >
                  Continue: {activePath.steps[activeStepIndex + 1].title}
                </button>
              )}
              {activeResponse && !hasNextStep && (
                <button onClick={restartPath} type="button">
                  Restart path
                </button>
              )}
            </form>
            {searchError && (
              <p className="error" role="alert">
                The search service is unavailable.
              </p>
            )}
            {activeResponse && (
              <>
                <StepInsight
                  detail={activeStep.detail}
                  previousResponse={previousResponse}
                  response={activeResponse}
                />
                {activeResponse.action ? (
                  <ActionRouteCard response={activeResponse} />
                ) : (
                  <ResultList
                    compact
                    response={activeResponse}
                    visibleLimit={3}
                  />
                )}
              </>
            )}
          </section>
          <aside className="speaker-note" aria-label="Presenter note">
            <p className="label">Key takeaway</p>
            <p>{activeStep.narration}</p>
            <button onClick={restartPath} type="button">
              Reset this path
            </button>
          </aside>
        </div>
        <details className="technical-details">
          <summary>Technical details and observability</summary>
          <div className="technical-grid">
            <section className="search-flow" aria-labelledby="flow-heading">
              <h3 id="flow-heading">Execution trace</h3>
              <ol>
                {flowSteps.map((step) => (
                  <li key={step.title}>
                    <strong>{step.title}</strong>
                    <span>{step.detail}</span>
                  </li>
                ))}
              </ol>
            </section>
            <section className="timing-panel" aria-labelledby="timing-heading">
              <h3 id="timing-heading">Request timing</h3>
              <TimingPanel search={search} roundTripMs={roundTripMs} />
            </section>
            <section
              className="routing-panel"
              aria-labelledby="routing-heading"
            >
              <h3 id="routing-heading">Route decision</h3>
              <RoutingPanel search={search} />
            </section>
            <section className="policy-panel" aria-labelledby="policy-heading">
              <h3 id="policy-heading">Policy contribution</h3>
              <PolicyPanel
                search={search}
                profileName={profileName}
                promotionName={promotionName}
              />
            </section>
            <section
              className="reranker-panel"
              aria-labelledby="reranker-heading"
            >
              <h3 id="reranker-heading">Reranker</h3>
              <RerankerPanel search={search} />
            </section>
            <section
              className="telemetry-panel"
              aria-labelledby="telemetry-heading"
            >
              <h3 id="telemetry-heading">Demo telemetry</h3>
              <TelemetryPanel telemetry={telemetry} />
            </section>
            <section
              className="redis-query-panel"
              aria-labelledby="redis-query-heading"
            >
              <h3 id="redis-query-heading">Redis Search queries</h3>
              <RedisQueryPanel search={search} />
            </section>
          </div>
          <ScorecardPanel
            evaluation={evaluation}
            isAvailable={isReady}
            isRunning={isEvaluating}
            onRun={() => void handleRunEvaluation()}
            isLoadRunning={isLoadTesting}
            loadConcurrency={loadConcurrency}
            loadTest={loadTest}
            onLoadConcurrencyChange={setLoadConcurrency}
            onRunLoad={() => void handleRunLoadTest()}
            rerankerName={rerankerName}
          />
        </details>
      </section>
      <footer>
        {config?.disclaimer ??
          "All catalog records, personas, tenants, promotions, and events are synthetic demo data."}
      </footer>
    </main>
  );
}
