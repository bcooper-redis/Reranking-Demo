import { describe, expect, it } from "vitest";

import { getRetailerExperience } from ".";

describe("retailer experiences", () => {
  it("keeps BHN as the default experience until another catalog is active", () => {
    const experience = getRetailerExperience("bhn");

    expect(experience.id).toBe("bhn");
    expect(experience.theme.accent).toBe("#008a71");
    expect(experience.demoPaths).toHaveLength(5);
    expect(getRetailerExperience("unknown")).toBe(experience);
  });

  it("keeps the guided prompts aligned to the BHN catalog and service paths", () => {
    const paths = Object.fromEntries(
      getRetailerExperience("bhn").demoPaths.map((path) => [path.id, path]),
    );

    expect(paths["teacher-relevance"]).toMatchObject({
      label: "Customer search",
      query: "coffee gift for my child's teacher",
    });
    expect(paths["prefix-discovery"]).toMatchObject({
      label: "Short-prefix discovery",
      query: "Star",
    });
    expect(paths["prefix-discovery"].steps[1]).toMatchObject({
      prefixMatching: true,
    });
    expect(paths["exact-brand"]).toMatchObject({ query: "Best Buy" });
    expect(paths["service-routing"]).toMatchObject({
      query: "check my balance",
    });
    expect(paths.personalization).toMatchObject({
      query: "a birthday gift for a gamer",
    });
  });

  it("builds catalog-aware e-commerce paths for an imported retailer", () => {
    const experience = getRetailerExperience("new-company", {
      accent: "#123456",
      accent_strong: "#0A2340",
      accent_soft: "#EAF2F8",
      canvas: "#F7F9FA",
    }, {
      customer_query: "trail running gift for trail runners",
      exact_product_query: "Trail Runner",
      preference_query: "a gift for trail runners",
      preference_profile_id: "catalog_preference",
      preference_profile_name: "Trail Running Shopper",
      preference_category: "Trail Running",
      prefix_query: "trail",
      prefix_expected_product: "Trailblazer Runner",
    });

    expect(experience.id).toBe("new-company");
    expect(experience.theme.accent).toBe("#123456");
    expect(experience.demoPaths).toHaveLength(5);
    expect(experience.demoPaths.map((path) => path.label)).toEqual([
      "Customer search",
      "Short-prefix discovery",
      "Exact product confidence",
      "Order support",
      "Bounded shopping preference",
    ]);
    expect(experience.demoPaths[0].query).toBe("trail running gift for trail runners");
    expect(experience.demoPaths[1]).toMatchObject({
      query: "trail",
      steps: [{ prefixMatching: false }, { prefixMatching: true }],
    });
    expect(experience.demoPaths[2].query).toBe("Trail Runner");
    expect(experience.demoPaths[3].query).toBe("where is my order");
    expect(experience.demoPaths[4].steps[1].actionLabel).toBe(
      "Apply Trail Running Shopper",
    );
  });
});
