import { BHN_EXPERIENCE } from "./bhn";
import type { DemoPath, RetailerExperience } from "./types";

type ImportedTheme = {
  accent: string;
  accent_strong: string;
  accent_soft: string;
  canvas: string;
} | null;

type ImportedDemoPrompts = {
  customer_query: string;
  exact_product_query: string;
  preference_query: string;
  preference_profile_id: string;
  preference_profile_name: string;
  preference_category: string;
  prefix_query?: string;
  prefix_expected_product?: string;
} | null;

const RETAILER_EXPERIENCES: Record<string, RetailerExperience> = {
  [BHN_EXPERIENCE.id]: BHN_EXPERIENCE,
};

export function getRetailerExperience(
  retailerId: string,
  importedTheme: ImportedTheme = null,
  demoPrompts: ImportedDemoPrompts = null,
): RetailerExperience {
  if (RETAILER_EXPERIENCES[retailerId]) return RETAILER_EXPERIENCES[retailerId];
  return importedTheme
    ? customExperience(retailerId, importedTheme, demoPrompts)
    : BHN_EXPERIENCE;
}

function customExperience(
  retailerId: string,
  importedTheme: ImportedTheme,
  demoPrompts: ImportedDemoPrompts,
): RetailerExperience {
  const accent = importedTheme?.accent ?? "#007a5e";
  const accentStrong = importedTheme?.accent_strong ?? "#005f49";
  const accentSoft = importedTheme?.accent_soft ?? "#e1f2ec";
  const prompts = demoPrompts ?? {
    customer_query: "a thoughtful gift for an online shopper",
    exact_product_query: "popular products",
    preference_query: "a gift for an online shopper",
    preference_profile_id: "catalog_preference",
    preference_profile_name: "Category Shopper",
    preference_category: "catalog category",
    prefix_query: undefined,
    prefix_expected_product: undefined,
  };
  return {
    id: retailerId,
    theme: {
      accent,
      accentBorder: accentSoft,
      accentStrong,
      accentSoft,
      bodyMuted: "#4d6473",
      canvas: importedTheme?.canvas ?? "#f1f5f4",
      codeSurface: "#e4ece9",
      heading: "#172d39",
      ink: "#172d39",
      muted: "#526a78",
      panel: "#ffffff",
      border: "#c8d4d5",
      borderSoft: "#dce5e4",
      focus: accent,
      successInk: "#075b4c",
      successSoft: "#e1f0eb",
      subtle: "#70828b",
    },
    demoPaths: ([
      {
        id: "customer-search",
        label: "Customer search",
        summary: "Show how text, semantic retrieval, and re-ranking refine a natural shopping request.",
        query: prompts.customer_query,
        steps: [
          {
            title: "Start with text retrieval",
            actionLabel: "Run text search",
            detail: "Text retrieval starts with the shopper's literal request and matching catalog fields.",
            narration: "We establish the keyword baseline against this retailer's catalog.",
            mode: "baseline",
            profileId: "anonymous",
            promotionId: null,
          },
          {
            title: "Add semantic retrieval",
            actionLabel: "Add semantic signal",
            detail: "RedisVL combines text and vector candidates using reciprocal-rank fusion.",
            narration: "The vector signal brings related catalog meaning into the candidate set.",
            mode: "hybrid",
            profileId: "anonymous",
            promotionId: null,
          },
          {
            title: "Re-rank the candidates",
            actionLabel: "Run cross-encoder",
            detail: "The cross-encoder evaluates the complete request against the hybrid candidates.",
            narration: "The final ordering applies deeper relevance work only to the Redis candidate set.",
            mode: "reranked",
            profileId: "anonymous",
            promotionId: null,
          },
        ],
      },
      {
        id: "prefix-discovery",
        label: "Short-prefix discovery",
        summary: "Show why a short literal query can miss the intended brand until Redis Search adds a prefix lookup.",
        query: prompts.prefix_query ?? "",
        steps: [
          {
            title: "Search the literal word",
            actionLabel: "Run literal text search",
            detail: `With prefix search off, Redis full-text retrieval only matches the literal word. Related catalog products can appear before the intended ${prompts.prefix_expected_product ?? "product"}.`,
            narration: "A short entry is ambiguous: it may be a word in catalog content, or the beginning of the product the shopper intended.",
            mode: "baseline",
            profileId: "anonymous",
            promotionId: null,
            prefixMatching: false,
          },
          {
            title: "Add brand and alias prefix search",
            actionLabel: "Find the intended product",
            detail: `Redis Search adds a dedicated brand-and-alias prefix lookup, so ${prompts.prefix_expected_product ?? "the intended product"} can join the same result set with visible prefix evidence.`,
            narration: "The prefix index solves the partial-entry problem without replacing normal text retrieval or requiring a special model.",
            mode: "baseline",
            profileId: "anonymous",
            promotionId: null,
            prefixMatching: true,
          },
        ],
      },
      {
        id: "exact-product",
        label: "Exact product confidence",
        summary: "Show that a named product remains prominent while retrieval becomes more nuanced.",
        query: prompts.exact_product_query,
        steps: [
          {
            title: "Retrieve product candidates",
            actionLabel: "Find this product",
            detail: "Hybrid retrieval combines literal product evidence with semantic catalog candidates.",
            narration: "A precise product request begins by honoring the product the shopper named.",
            mode: "hybrid",
            profileId: "anonymous",
            promotionId: null,
          },
          {
            title: "Verify the final ranking",
            actionLabel: "Verify exact match",
            detail: "Re-ranking uses the full request while exact product and alias matches remain protected.",
            narration: "The re-ranker adds nuance without pushing an explicit product request aside.",
            mode: "reranked",
            profileId: "anonymous",
            promotionId: null,
          },
        ],
      },
      {
        id: "order-support",
        label: "Order support",
        summary: "Show SemanticRouter directing an operational request to the useful journey instead of product retrieval.",
        query: "where is my order",
        steps: [
          {
            title: "Classify the request",
            actionLabel: "Route this request",
            detail: "SemanticRouter recognizes order tracking and returns the configured self-service journey without catalog retrieval.",
            narration: "Not every e-commerce request is a search. RedisVL selects the right action before retrieval begins.",
            mode: "baseline",
            profileId: "anonymous",
            promotionId: null,
          },
        ],
      },
      {
        id: "personalization",
        label: "Bounded shopping preference",
        summary: "Show a transparent category preference shifting eligible products without changing retrieval itself.",
        query: prompts.preference_query,
        steps: [
          {
            title: "Search without a profile",
            actionLabel: "Search anonymously",
            detail: "The re-ranker orders results from the customer request and catalog evidence, without a profile preference.",
            narration: "First, this is the neutral answer: the same retrieval and re-ranking pipeline with no profile signal.",
            mode: "reranked",
            profileId: "anonymous",
            promotionId: null,
          },
          {
            title: "Apply a declared preference",
            actionLabel: `Apply ${prompts.preference_profile_name}`,
            detail: `Eligible ${prompts.preference_category} products receive a bounded policy contribution; the result evidence remains visible.`,
            narration: "Now we add one declared preference, separate from the retrieval and re-ranking evidence.",
            mode: "reranked",
            profileId: prompts.preference_profile_id,
            promotionId: null,
          },
        ],
      },
    ] as DemoPath[]).filter(
      (path) => path.id !== "prefix-discovery" || Boolean(prompts.prefix_query),
    ),
  };
}

export type {
  DemoPath,
  DemoStep,
  RetailerExperience,
  RetailerTheme,
} from "./types";
