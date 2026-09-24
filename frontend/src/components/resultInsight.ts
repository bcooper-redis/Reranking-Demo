import type { SearchResponse } from "../api/search";

export function resultInsight(
  response: SearchResponse,
  previous: SearchResponse | null,
) {
  const winner = response.results[0];
  const prior = previous?.results[0];
  if (response.action)
    return {
      title: "A service request, routed directly",
      detail: "Product retrieval was skipped.",
    };
  if (!winner)
    return {
      title: "No matching products",
      detail: "Try another request or continue to the next search step.",
    };
  const changed = prior && prior.id !== winner.id;
  const score = winner.score_breakdown;
  const title = changed
    ? `${winner.brand_name} moves to first place`
    : previous
      ? `${winner.brand_name} stays in first place`
      : `${winner.brand_name} leads the results`;
  const detail = score?.prefix_match
    ? "Matched the beginning of a brand or alias. Prefix matches are promoted."
    : score?.exact_match
      ? "An exact brand or alias match protects this result."
      : response.mode === "reranked"
        ? "The selected cross-encoder scored the hybrid candidates against the full request."
        : response.mode === "hybrid"
          ? "Text and vector rankings were combined using reciprocal-rank fusion."
          : "The request matches words in the catalog.";
  return { title, detail };
}
