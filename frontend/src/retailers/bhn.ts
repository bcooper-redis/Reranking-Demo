import type { RetailerExperience } from "./types";

export const BHN_EXPERIENCE: RetailerExperience = {
  id: "bhn",
  theme: {
    accent: "#008a71",
    accentBorder: "#9abeb2",
    accentStrong: "#006d59",
    accentSoft: "#e0f1ec",
    bodyMuted: "#486276",
    canvas: "#eef2f3",
    codeSurface: "#e3ebee",
    heading: "#173448",
    ink: "#152535",
    muted: "#446174",
    panel: "#ffffff",
    border: "#bdcbd2",
    borderSoft: "#d5dfe3",
    focus: "#66b9a9",
    successInk: "#075b4c",
    successSoft: "#e1f0eb",
    subtle: "#6a7d88",
  },
  demoPaths: [
    {
      id: "teacher-relevance",
      label: "Customer search",
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
      id: "prefix-discovery",
      label: "Short-prefix discovery",
      summary:
        "Show why a short literal query can surface entertainment content before Redis Search adds the intended brand prefix.",
      query: "Star",
      steps: [
        {
          title: "Search the literal word",
          actionLabel: "Run literal text search",
          detail:
            "With brand prefix search off, text retrieval sees the literal word star and returns entertainment-related cards that contain it.",
          narration:
            "A customer may mean a whole word, or they may have stopped halfway through a brand. Normal text search has no reason to assume the latter.",
          mode: "baseline",
          profileId: "anonymous",
          promotionId: null,
          prefixMatching: false,
        },
        {
          title: "Add brand and alias prefix search",
          actionLabel: "Find Starbucks",
          detail:
            "Redis Search adds a brand-and-alias prefix lookup, promoting Starbucks eGift with visible prefix evidence while keeping the text results available.",
          narration:
            "The prefix index turns a partial entry into an intentional brand match without a new model or a separate search system.",
          mode: "baseline",
          profileId: "anonymous",
          promotionId: null,
          prefixMatching: true,
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
  ],
};
