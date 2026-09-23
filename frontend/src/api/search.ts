export type Tenant = {
  id: string;
  display_name: string;
  allowed_delivery_types: string[];
  promotion_ids: string[];
};

export type Profile = {
  id: string;
  display_name: string;
};

export type Promotion = {
  id: string;
  display_name: string;
  eligible_tenant_ids: string[];
};

export type Reranker = {
  id: string;
  display_name: string;
  provider: string;
  model: string;
};

export type Retailer = {
  id: string;
  organization_name: string;
  experience_name: string;
  experience_subtitle: string;
  catalog_label: string;
  theme: {
    accent: string;
    accent_strong: string;
    accent_soft: string;
    canvas: string;
  } | null;
  demo_prompts: {
    customer_query: string;
    exact_product_query: string;
    preference_query: string;
    preference_profile_id: string;
    preference_profile_name: string;
    preference_category: string;
    prefix_query?: string;
    prefix_expected_product?: string;
  } | null;
};

export type RetailerImportPayload = {
  organization_name: string;
  experience_name: string;
  catalog_label: string;
  theme: {
    accent: string;
    accent_strong: string;
    accent_soft: string;
    canvas: string;
  };
  demo_paths?: {
    customer_query: string;
    exact_product_query: string;
    preference_query: string;
    preference_profile_name: string;
    preference_category: string;
    prefix_query: string;
    prefix_expected_product: string;
  };
  products: {
    brand_name: string;
    description: string;
    aliases?: string[];
    categories: string[];
    recipient_tags?: string[];
    delivery_types?: string[];
    min_price?: number;
    max_price?: number;
  }[];
};

export type RetailerImportResponse = {
  retailer_id: string;
  organization_name: string;
  experience_name: string;
  catalog_count: number;
  index_alias: string;
};

export type RetailerDeleteResponse = {
  retailer_id: string;
};

export type PublicConfig = {
  retailer: Retailer;
  retailers: Retailer[];
  tenants: Tenant[];
  profiles: Profile[];
  promotions: Promotion[];
  rerankers: Reranker[];
  modes: ["baseline", "hybrid", "reranked", "compare"];
  catalog_count: number;
  disclaimer: string;
};

export type ProductResult = {
  id: string;
  brand_name: string;
  description: string;
  categories: string[];
  delivery_types: string[];
  min_denomination: number;
  max_denomination: number;
  promoted: boolean;
  score: number | null;
  score_breakdown: {
    exact_match: boolean;
    prefix_match: boolean;
    lexical_score: number | null;
    lexical_rank: number | null;
    vector_distance: number | null;
    vector_rank: number | null;
    hybrid_score: number | null;
    reranker_score: number | null;
    matching_fields: string[];
    personalization_boost: number;
    promotion_boost: number;
    popularity_tiebreaker: number;
    final_score: number | null;
  } | null;
};

export type SearchSuggestion = {
  id: string;
  brand_name: string;
};

export type AutocompleteResponse = {
  query: string;
  suggestions: SearchSuggestion[];
  redis_search_query: {
    label: string;
    statement: string;
    parameters: string[];
  } | null;
};

export type SearchMode = "baseline" | "hybrid" | "reranked" | "compare";

export type IntentDecision = {
  name:
    | "product_search"
    | "balance_check"
    | "card_activation"
    | "order_status"
    | "customer_support";
  confidence: number;
  distance: number | null;
  threshold: number | null;
  fallback: boolean;
  source: string;
};

export type ActionCard = {
  intent: IntentDecision["name"];
  title: string;
  description: string;
  destination_label: string;
};

export type SearchResponse = {
  request_id: string;
  query: string;
  mode: Exclude<SearchMode, "compare">;
  results: ProductResult[];
  timings_ms: Record<string, number>;
  intent: IntentDecision | null;
  action: ActionCard | null;
  redis_search_queries: {
    label: string;
    statement: string;
    parameters: string[];
  }[];
  diagnostics: Record<string, string | number | boolean> | null;
  fallbacks: string[];
};

export type ComparisonResponse = {
  request_id: string;
  query: string;
  mode: "compare";
  comparisons: {
    baseline: SearchResponse;
    hybrid: SearchResponse;
    reranked: SearchResponse;
  };
};

export type EvaluationMetrics = {
  query_count: number;
  product_query_count: number;
  exact_brand_hit_at_1: number;
  mrr: number;
  ndcg_at_10: number;
  recall_at_25: number;
  route_accuracy: number;
  latency_p50_ms: number;
  latency_p95_ms: number;
};

export type EvaluationRun = {
  id: string;
  created_at: string;
  configuration: Record<string, string | number>;
  metrics: Record<Exclude<SearchMode, "compare">, EvaluationMetrics>;
};

export type LoadTestMetrics = {
  request_count: number;
  error_count: number;
  fallback_count: number;
  latency_p50_ms: number;
  latency_p95_ms: number;
};

export type LoadTestRun = {
  id: string;
  created_at: string;
  configuration: Record<string, string | number>;
  concurrency: number;
  rounds: number;
  metrics: Record<Exclude<SearchMode, "compare">, LoadTestMetrics>;
};

export type TelemetrySnapshot = {
  request_count: number;
  error_count: number;
  fallback_count: number;
  route_distribution: Record<string, number>;
  latency_p50_ms: number;
  latency_p95_ms: number;
  click_count: number;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const retailerStorageKey = "giftfind-demo-retailer";

class ApiRequestError extends Error {
  constructor(readonly status: number) {
    super(`API request failed with ${status}`);
  }
}

export function getActiveRetailerId(): string {
  return window.localStorage.getItem(retailerStorageKey) ?? "bhn";
}

export function setActiveRetailerId(retailerId: string): void {
  window.localStorage.setItem(retailerStorageKey, retailerId);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("X-Demo-Retailer", getActiveRetailerId());
  const response = await fetch(`${apiBaseUrl}${path}`, { ...init, headers });
  if (!response.ok)
    throw new ApiRequestError(response.status);
  return (await response.json()) as T;
}

export async function getPublicConfig(signal?: AbortSignal): Promise<PublicConfig> {
  try {
    return await request<PublicConfig>("/api/v1/config/public", { signal });
  } catch (error) {
    if (
      error instanceof ApiRequestError &&
      error.status === 400 &&
      getActiveRetailerId() !== "bhn"
    ) {
      setActiveRetailerId("bhn");
      return request<PublicConfig>("/api/v1/config/public", { signal });
    }
    throw error;
  }
}

export function importRetailer(
  payload: RetailerImportPayload,
): Promise<RetailerImportResponse> {
  return request<RetailerImportResponse>("/api/v1/retailers/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function deleteRetailer(
  retailerId: string,
): Promise<RetailerDeleteResponse> {
  return request<RetailerDeleteResponse>(`/api/v1/retailers/${retailerId}`, {
    method: "DELETE",
  });
}

export function searchCatalog(
  query: string,
  tenantId: string,
  profileId: string,
  promotionId: string | null,
  mode: SearchMode,
  rerankerId: string,
  prefixMatching: boolean,
): Promise<SearchResponse | ComparisonResponse> {
  return request<SearchResponse | ComparisonResponse>("/api/v1/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      tenant_id: tenantId,
      profile_id: profileId,
      promotion_id: promotionId,
      mode,
      reranker_id: rerankerId,
      prefix_matching: prefixMatching,
      debug: true,
    }),
  });
}

export function getSearchSuggestions(
  query: string,
  tenantId: string,
  signal?: AbortSignal,
): Promise<AutocompleteResponse> {
  const parameters = new URLSearchParams({ q: query, tenant_id: tenantId });
  return request<AutocompleteResponse>(
    `/api/v1/search/suggestions?${parameters.toString()}`,
    { signal },
  );
}

export function runEvaluation(rerankerId: string): Promise<EvaluationRun> {
  return request<EvaluationRun>("/api/v1/evaluations/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reranker_id: rerankerId }),
  });
}

export function runLoadTest(
  rerankerId: string,
  concurrency: number,
): Promise<LoadTestRun> {
  return request<LoadTestRun>("/api/v1/evaluations/load", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      reranker_id: rerankerId,
      concurrency,
      rounds: 3,
    }),
  });
}

export function getTelemetry(): Promise<TelemetrySnapshot> {
  return request<TelemetrySnapshot>("/api/v1/telemetry");
}

export function recordResultClick(
  requestId: string,
  resultId: string,
  mode: Exclude<SearchMode, "compare">,
  tenantId: string,
  profileId: string,
): Promise<{ event_id: string }> {
  return request("/api/v1/events/click", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      request_id: requestId,
      result_id: resultId,
      mode,
      tenant_id: tenantId,
      profile_id: profileId,
    }),
  });
}
