import { useState } from "react";
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Check,
  SearchX,
} from "lucide-react";
import type { ProductResult, SearchResponse } from "../api/search";
import { ProductArtwork } from "./ProductArtwork";

import { resultInsight } from "./resultInsight";

export function RetailResults({
  response,
  previous,
  retailerId,
  layout,
}: {
  response: SearchResponse;
  previous: SearchResponse | null;
  retailerId: string;
  layout: "grid" | "list";
}) {
  const [expanded, setExpanded] = useState(false);
  const results = expanded ? response.results : response.results.slice(0, 3);
  const priorRanks = new Map(
    previous?.results.map((result, index) => [result.id, index + 1]),
  );
  return (
    <section
      className={`retail-results ${layout}`}
      aria-label={`${response.mode} search results`}
    >
      {!results.length && (
        <div className="empty-results">
          <SearchX aria-hidden="true" />
          <h3>No products found</h3>
          <p>No catalog matches for &ldquo;{response.query}&rdquo;.</p>
        </div>
      )}
      <ol className="product-grid">
        {results.map((result, index) => {
          const priorRank = priorRanks.get(result.id);
          return (
            <li className="product-item" key={result.id}>
              <div className="product-visual">
                <ProductArtwork product={result} retailerId={retailerId} />
                <span className="product-rank">#{index + 1}</span>
                {result.score_breakdown?.exact_match ? (
                  <span className="product-badge">
                    <Check size={13} />
                    Exact match
                  </span>
                ) : result.score_breakdown?.prefix_match ? (
                  <span className="product-badge">
                    <Check size={13} />
                    Prefix match
                  </span>
                ) : null}
              </div>
              <div className="product-copy">
                <p className="product-category">
                  {result.categories.slice(0, 2).join(" / ")}
                </p>
                <h3>{result.brand_name}</h3>
                <p className="product-description">{result.description}</p>
                <div className="product-price">
                  <strong>
                    ${result.min_denomination}–${result.max_denomination}
                  </strong>
                  <span>{result.delivery_types.join(" / ")}</span>
                </div>
                {previous &&
                  (priorRank ? (
                    priorRank !== index + 1 && (
                      <p className="product-movement">
                        {priorRank > index + 1 ? (
                          <ArrowUpRight size={14} />
                        ) : (
                          <ArrowDown size={14} />
                        )}
                        Previously #{priorRank}
                      </p>
                    )
                  ) : (
                    <p className="product-movement">New to these results</p>
                  ))}
                {result.promoted && (
                  <span className="product-movement">Promoted</span>
                )}
                <details className="product-evidence">
                  <summary>Match details</summary>
                  <p>
                    {result.score_breakdown?.matching_fields.join("; ") ||
                      "No literal term overlap recorded."}
                  </p>
                  {result.score_breakdown?.lexical_rank != null && (
                    <p>
                      Text rank #{result.score_breakdown.lexical_rank}; score{" "}
                      {result.score_breakdown.lexical_score?.toFixed(4) ??
                        "unavailable"}
                    </p>
                  )}
                  {result.score_breakdown?.vector_rank != null && (
                    <p>Semantic rank #{result.score_breakdown.vector_rank}</p>
                  )}
                  {result.score_breakdown?.hybrid_score != null && (
                    <p>
                      RRF score {result.score_breakdown.hybrid_score.toFixed(4)}
                    </p>
                  )}
                  {result.score_breakdown?.reranker_score != null && (
                    <p>
                      Cross-encoder score{" "}
                      {result.score_breakdown.reranker_score.toFixed(4)}
                    </p>
                  )}
                  {Boolean(result.score_breakdown?.personalization_boost) && (
                    <p>
                      Preference contribution +
                      {result.score_breakdown!.personalization_boost.toFixed(4)}
                    </p>
                  )}
                  {Boolean(result.score_breakdown?.promotion_boost) && (
                    <p>
                      Promotion contribution +
                      {result.score_breakdown!.promotion_boost.toFixed(4)}
                    </p>
                  )}
                  {result.score_breakdown?.final_score != null && (
                    <p>
                      Final score{" "}
                      {result.score_breakdown.final_score.toFixed(4)}
                    </p>
                  )}
                </details>
              </div>
            </li>
          );
        })}
      </ol>
      {response.results.length > 3 && (
        <button
          className="text-command"
          type="button"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded
            ? "Show top 3"
            : `Show all ${response.results.length} results`}
          <ArrowRight size={16} />
        </button>
      )}
      {response.fallbacks.length > 0 && (
        <p className="fallback">Fallback: {response.fallbacks.join(", ")}</p>
      )}
    </section>
  );
}

function Winner({
  product,
  label,
  retailerId,
}: {
  product: ProductResult;
  label: string;
  retailerId: string;
}) {
  return (
    <div className="change-product">
      <p className="micro-label">{label}</p>
      <ProductArtwork product={product} retailerId={retailerId} />
      <strong>{product.brand_name}</strong>
    </div>
  );
}

export function ChangeSummary({
  response,
  previous,
  retailerId,
  detail,
  roundTripMs,
}: {
  response: SearchResponse | null;
  previous: SearchResponse | null;
  retailerId: string;
  detail: string;
  roundTripMs: number | null;
}) {
  const winner = response?.results[0];
  const prior = previous?.results[0];
  return (
    <aside className="change-sidebar" aria-label="Search explanation">
      <h2>{response ? "What changed" : "This step"}</h2>
      {prior && winner && (
        <>
          <Winner product={prior} label="Before" retailerId={retailerId} />
          <ArrowDown className="change-arrow" size={20} aria-hidden="true" />
          <Winner product={winner} label="After" retailerId={retailerId} />
        </>
      )}
      {response && !previous && (
        <p className="micro-label">
          {response.action ? "Service route" : "Initial results"}
        </p>
      )}
      {response && (
        <p className="change-explanation">
          {resultInsight(response, previous).detail}
        </p>
      )}
      {!response && <p className="change-explanation">{detail}</p>}
      {response && (
        <div className="sidebar-performance">
          <h3>Performance</h3>
          <dl>
            <div>
              <dt>{response.action ? "Routing" : "Redis retrieval"}</dt>
              <dd>
                {(response.action
                  ? response.timings_ms.routing
                  : response.timings_ms.retrieval
                )?.toFixed(2) ?? "–"}{" "}
                ms
              </dd>
            </div>
            {response.timings_ms.reranking != null && (
              <div>
                <dt>Re-ranking</dt>
                <dd>{response.timings_ms.reranking.toFixed(2)} ms</dd>
              </div>
            )}
            <div>
              <dt>Round trip</dt>
              <dd>{roundTripMs?.toFixed(0) ?? "–"} ms</dd>
            </div>
          </dl>
        </div>
      )}
    </aside>
  );
}
