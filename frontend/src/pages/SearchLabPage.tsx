import { useEffect, useState } from "react";
import type { CSSProperties, FormEvent, KeyboardEvent } from "react";
import {
  ArrowRight,
  Check,
  ChevronRight,
  Grid2X2,
  List,
  LoaderCircle,
  RotateCcw,
  Search,
  Settings2,
  X,
} from "lucide-react";
import { ChangeSummary, RetailResults } from "../components/RetailResults";
import { resultInsight } from "../components/resultInsight";

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
import {
  getRetailerExperience,
  type DemoPath,
  type RetailerTheme,
} from "../retailers";

type PageState =
  | { kind: "loading" }
  | { kind: "ready"; config: PublicConfig; readiness: Readiness }
  | { kind: "error" };

const BHN_DEMO_PATHS: DemoPath[] = getRetailerExperience("bhn").demoPaths;

const DEMO_PATHS: DemoPath[] = BHN_DEMO_PATHS;

function retailerThemeStyle(theme: RetailerTheme): CSSProperties {
  return {
    "--retailer-accent": theme.accent,
    "--retailer-accent-border": theme.accentBorder,
    "--retailer-accent-strong": theme.accentStrong,
    "--retailer-accent-soft": theme.accentSoft,
    "--retailer-body-muted": theme.bodyMuted,
    "--retailer-canvas": theme.canvas,
    "--retailer-code-surface": theme.codeSurface,
    "--retailer-heading": theme.heading,
    "--retailer-ink": theme.ink,
    "--retailer-muted": theme.muted,
    "--retailer-panel": theme.panel,
    "--retailer-border": theme.border,
    "--retailer-border-soft": theme.borderSoft,
    "--retailer-focus": theme.focus,
    "--retailer-success-ink": theme.successInk,
    "--retailer-success-soft": theme.successSoft,
    "--retailer-subtle": theme.subtle,
  } as CSSProperties;
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
  if (intent.source === "router_low_confidence") {
    return "No service route matched this product request, so Redis continued with product retrieval.";
  }
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
  const tenantId =
    page.kind === "ready"
      ? (page.config.tenants.find((tenant) => tenant.id === "general")?.id ??
        page.config.tenants[0]?.id ??
        "general")
      : "general";
  const [pathId, setPathId] = useState(DEMO_PATHS[0].id);
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [query, setQuery] = useState(DEMO_PATHS[0].query);
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [isSuggestionOpen, setIsSuggestionOpen] = useState(false);
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(-1);
  const [prefixMatchingEnabled, setPrefixMatchingEnabled] = useState(false);
  const [typeaheadEnabled, setTypeaheadEnabled] = useState(false);
  const [rerankerId, setRerankerId] = useState("minilm_l6");
  const [journey, setJourney] = useState<SearchResponse[]>([]);
  const [search, setSearch] = useState<SearchResponse | null>(null);
  const [searchError, setSearchError] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [resultLayout, setResultLayout] = useState<"grid" | "list">("grid");
  const [roundTripMs, setRoundTripMs] = useState<number | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationRun | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [loadTest, setLoadTest] = useState<LoadTestRun | null>(null);
  const [isLoadTesting, setIsLoadTesting] = useState(false);
  const [loadConcurrency, setLoadConcurrency] = useState(2);
  const [telemetry, setTelemetry] = useState<TelemetrySnapshot | null>(null);
  const selectedRetailerId =
    page.kind === "ready" ? page.config.retailer.id : null;

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
    if (!selectedRetailerId) return;
    const nextPath = getRetailerExperience(
      selectedRetailerId,
      page.kind === "ready" ? page.config.retailer.theme : null,
      page.kind === "ready" ? page.config.retailer.demo_prompts : null,
    ).demoPaths[0];
    setPathId(nextPath.id);
    setQuery(nextPath.query);
    setActiveStepIndex(0);
    setJourney([]);
    setSearch(null);
    setRoundTripMs(null);
    setSearchError(false);
  }, [page, selectedRetailerId]);

  useEffect(() => {
    const normalizedQuery = query.trim();
    if (
      !typeaheadEnabled ||
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
  }, [query, tenantId, typeaheadEnabled]);

  const config = page.kind === "ready" ? page.config : null;
  const retailerExperience = getRetailerExperience(
    config?.retailer.id ?? "bhn",
    config?.retailer.theme ?? null,
    config?.retailer.demo_prompts ?? null,
  );
  const demoPaths = retailerExperience.demoPaths;
  const activePath =
    demoPaths.find((candidate) => candidate.id === pathId) ?? demoPaths[0];
  const activeStep = activePath.steps[activeStepIndex];
  const activeResponse = journey[activeStepIndex] ?? null;
  const previousResponse =
    activeStepIndex > 0 &&
    journey[activeStepIndex - 1]?.query === (activeResponse?.query ?? query)
      ? journey[activeStepIndex - 1]
      : null;
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
        prefixMatchingEnabled,
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
      demoPaths.find((candidate) => candidate.id === nextPathId) ??
      demoPaths[0];
    setPathId(nextPath.id);
    setQuery(nextPath.query);
    setPrefixMatchingEnabled(nextPath.steps[0].prefixMatching ?? false);
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
    setPrefixMatchingEnabled(activePath.steps[0].prefixMatching ?? false);
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

  const insight = activeResponse
    ? resultInsight(activeResponse, previousResponse)
    : null;

  return (
    <main
      className="retail-showcase"
      data-retailer={retailerExperience.id}
      style={retailerThemeStyle(retailerExperience.theme)}
    >
      <header className="retail-header">
        <div className="retail-identity">
          <a href="/" className="experience-name">
            {config?.retailer.experience_name ?? "GiftFind"}
          </a>
          <span>
            {config?.retailer.organization_name ?? "Blackhawk Networks"}
          </span>
        </div>
        <div className="retail-header-tools">
          <span
            className={
              isReady ? "connection-status connected" : "connection-status"
            }
            aria-live="polite"
          >
            <span aria-hidden="true" />
            {isReady
              ? "Redis connected"
              : page.kind === "error"
                ? "Runtime unavailable"
                : "Checking runtime"}
          </span>
          <a
            className="icon-command"
            href="/?view=configuration"
            title="Internal demo configuration"
            aria-label="Open internal demo configuration"
          >
            <Settings2 size={20} />
          </a>
        </div>
      </header>

      <section className="retail-search" aria-labelledby="search-heading">
        <div className="retail-search-heading">
          <h1 id="search-heading">
            {config?.retailer.experience_subtitle ?? "RedisVL Relevance Lab"}
          </h1>
          <span>
            {config
              ? `${config.catalog_count} ${config.retailer.catalog_label}`
              : "Loading catalog"}
          </span>
        </div>
        <form className="retail-search-form" onSubmit={runStep}>
          <div className="retail-search-input autocomplete">
            <Search size={22} aria-hidden="true" />
            <input
              aria-label="Customer request"
              role="combobox"
              aria-autocomplete="list"
              aria-controls="redis-suggestions"
              aria-activedescendant={
                isSuggestionOpen && activeSuggestionIndex >= 0
                  ? `suggestion-${activeSuggestionIndex}`
                  : undefined
              }
              aria-expanded={
                typeaheadEnabled && isSuggestionOpen && suggestions.length > 0
              }
              disabled={isSearching}
              onChange={(event) => {
                setQuery(event.target.value);
                setIsSuggestionOpen(typeaheadEnabled);
                setActiveSuggestionIndex(-1);
              }}
              onFocus={() => setIsSuggestionOpen(typeaheadEnabled)}
              onBlur={() => setIsSuggestionOpen(false)}
              onKeyDown={handleSuggestionKeyDown}
              value={query}
            />
            {query && (
              <button
                className="icon-command"
                type="button"
                title="Clear search"
                aria-label="Clear search"
                disabled={isSearching}
                onClick={() => {
                  setQuery("");
                  setSuggestions([]);
                }}
              >
                <X size={18} />
              </button>
            )}
            {typeaheadEnabled && isSuggestionOpen && suggestions.length > 0 && (
              <div
                className="autocomplete-menu"
                id="redis-suggestions"
                role="listbox"
              >
                <p>Redis Search suggestions</p>
                {suggestions.map((suggestion, index) => (
                  <button
                    id={`suggestion-${index}`}
                    aria-selected={index === activeSuggestionIndex}
                    className={index === activeSuggestionIndex ? "active" : ""}
                    key={suggestion.id}
                    onMouseDown={(event) => event.preventDefault()}
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
          <button
            className="primary-command"
            disabled={isSearching || !isReady || !query.trim()}
            type="submit"
          >
            {isSearching ? (
              <LoaderCircle className="spin" size={18} />
            ) : (
              <Search size={18} />
            )}
            {isSearching ? "Searching" : activeStep.actionLabel}
          </button>
        </form>
        {page.kind === "error" && (
          <p className="error" role="alert">
            The demo could not connect to the service.{" "}
            <a href="/">Retry connection</a>
          </p>
        )}
        {searchError && (
          <p className="error" role="alert">
            The search service is unavailable. Please try again.
          </p>
        )}
      </section>

      <section className="presenter-bar" aria-label="Demo controls">
        <label className="retail-path">
          <span>Demo path</span>
          <select
            aria-label="Path"
            disabled={isSearching}
            onChange={(event) => choosePath(event.target.value)}
            value={activePath.id}
          >
            {demoPaths.map((path) => (
              <option key={path.id} value={path.id}>
                {path.label}
              </option>
            ))}
          </select>
        </label>
        <ol className="retail-steps" aria-label="Demo steps">
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
              aria-current={index === activeStepIndex ? "step" : undefined}
            >
              <span className="step-number">
                {index < activeStepIndex ? <Check size={13} /> : index + 1}
              </span>
              <span>{step.title}</span>
            </li>
          ))}
        </ol>
        <div className="retail-switches">
          <label className="retail-switch">
            <input
              type="checkbox"
              role="switch"
              checked={prefixMatchingEnabled}
              disabled={isSearching}
              onChange={(event) =>
                setPrefixMatchingEnabled(event.target.checked)
              }
            />
            <span>Brand prefix</span>
          </label>
          <label className="retail-switch">
            <input
              type="checkbox"
              role="switch"
              checked={typeaheadEnabled}
              disabled={isSearching}
              onChange={(event) => setTypeaheadEnabled(event.target.checked)}
            />
            <span>Typeahead</span>
          </label>
          <button
            className="icon-command"
            type="button"
            title="Reset this path"
            aria-label="Reset this path"
            disabled={isSearching}
            onClick={restartPath}
          >
            <RotateCcw size={18} />
          </button>
        </div>
      </section>

      <div className="retail-body">
        <section
          className="retail-stage"
          aria-labelledby="stage-heading"
          aria-busy={isSearching}
        >
          <div className="retail-stage-heading">
            <div>
              <p className="micro-label">
                Step {activeStepIndex + 1} of {activePath.steps.length}
              </p>
              <h2 id="stage-heading">{activeStep.title}</h2>
            </div>
            <div
              className="view-switch"
              role="group"
              aria-label="Result layout"
            >
              <button
                type="button"
                className="icon-command"
                title="Product grid"
                aria-label="Product grid"
                aria-pressed={resultLayout === "grid"}
                onClick={() => setResultLayout("grid")}
              >
                <Grid2X2 size={18} />
              </button>
              <button
                type="button"
                className="icon-command"
                title="Product list"
                aria-label="Product list"
                aria-pressed={resultLayout === "list"}
                onClick={() => setResultLayout("list")}
              >
                <List size={19} />
              </button>
            </div>
          </div>
          {activeStep.mode === "reranked" && (
            <label className="retail-reranker">
              <span>Reranker</span>
              <select
                disabled={isSearching}
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
          {activeResponse && insight ? (
            <>
              <div className="retail-next">
                <p>{activeStep.narration}</p>
                {hasNextStep ? (
                  <button
                    className="primary-command"
                    type="button"
                    disabled={isSearching || query !== activeResponse.query}
                    onClick={() => {
                      const nextStep = activePath.steps[activeStepIndex + 1];
                      if (nextStep.prefixMatching !== undefined)
                        setPrefixMatchingEnabled(nextStep.prefixMatching);
                      setActiveStepIndex((index) => index + 1);
                      setRoundTripMs(null);
                    }}
                  >
                    Continue: {activePath.steps[activeStepIndex + 1].title}
                    <ArrowRight size={18} />
                  </button>
                ) : (
                  <button
                    className="text-command"
                    disabled={isSearching}
                    onClick={restartPath}
                    type="button"
                  >
                    <RotateCcw size={16} />
                    Restart path
                  </button>
                )}
              </div>
              <div className="retail-insight" aria-live="polite">
                <Check size={18} />
                <div>
                  <strong>{insight.title}</strong>
                  <p>{insight.detail}</p>
                </div>
              </div>
              <div className="retail-result-meta">
                <span>Results for &ldquo;{activeResponse.query}&rdquo;</span>
                <span>{activeResponse.results.length} results</span>
              </div>
              {activeResponse.action ? (
                <ActionRouteCard response={activeResponse} />
              ) : (
                <RetailResults
                  key={`${activeStepIndex}-${activeResponse.query}`}
                  response={activeResponse}
                  previous={previousResponse}
                  retailerId={retailerExperience.id}
                  layout={resultLayout}
                />
              )}
            </>
          ) : (
            <div className="retail-ready">
              <Search size={32} aria-hidden="true" />
              <h3>
                {isSearching
                  ? "Finding the best matches"
                  : "Ready when you are"}
              </h3>
              <p>{activeStep.detail}</p>
            </div>
          )}
        </section>
        <ChangeSummary
          response={activeResponse}
          previous={previousResponse}
          retailerId={retailerExperience.id}
          detail={activeStep.narration}
          roundTripMs={roundTripMs}
        />
      </div>

      <section
        className="retail-observability"
        aria-label="Technical details and observability"
      >
        <details className="technical-details">
          <summary>
            <ChevronRight size={18} />
            Execution and timing
          </summary>
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
            <section className="timing-panel">
              <h3>Request timing</h3>
              <TimingPanel search={search} roundTripMs={roundTripMs} />
            </section>
            <section className="routing-panel">
              <h3>Route decision</h3>
              <RoutingPanel search={search} />
            </section>
            <section className="policy-panel">
              <h3>Policy contribution</h3>
              <PolicyPanel
                search={search}
                profileName={profileName}
                promotionName={promotionName}
              />
            </section>
            <section className="reranker-panel">
              <h3>Reranker</h3>
              <RerankerPanel search={search} />
            </section>
            <section className="telemetry-panel">
              <h3>Demo telemetry</h3>
              <TelemetryPanel telemetry={telemetry} />
            </section>
          </div>
        </details>
        <details className="technical-details">
          <summary>
            <ChevronRight size={18} />
            Redis Search queries
          </summary>
          <RedisQueryPanel search={search} />
        </details>
        <details className="technical-details">
          <summary>
            <ChevronRight size={18} />
            Golden query scorecard and load testing
          </summary>
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
      <footer className="retail-footer">
        <span className="redisvl-credit">
          Made with <strong>RedisVL</strong>
        </span>
        <p>{config?.disclaimer ?? "Synthetic demo data."}</p>
      </footer>
    </main>
  );
}
