import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getActiveRetailerId, getPublicConfig, setActiveRetailerId } from "./search";

const bhnConfig = {
  retailer: {
    id: "bhn",
    organization_name: "Blackhawk Networks",
    experience_name: "GiftFind",
    experience_subtitle: "RedisVL Relevance Lab",
    catalog_label: "catalog cards",
    theme: null,
    demo_prompts: null,
  },
  retailers: [],
  tenants: [],
  profiles: [],
  promotions: [],
  rerankers: [],
  modes: ["baseline", "hybrid", "reranked", "compare"],
  catalog_count: 360,
  disclaimer: "Synthetic demo data.",
};

describe("getPublicConfig", () => {
  const values = new Map<string, string>();
  const storage = {
    clear: () => values.clear(),
    getItem: (key: string) => values.get(key) ?? null,
    removeItem: (key: string) => values.delete(key),
    setItem: (key: string, value: string) => values.set(key, value),
  };

  beforeEach(() => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: storage,
    });
  });

  afterEach(() => {
    storage.clear();
    vi.unstubAllGlobals();
  });

  it("recovers from a deleted saved retailer by returning to BHN", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 400 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify(bhnConfig), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchMock);
    setActiveRetailerId("academy-sports-outdoors");

    const config = await getPublicConfig();

    expect(config.retailer.id).toBe("bhn");
    expect(getActiveRetailerId()).toBe("bhn");
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(new Headers(fetchMock.mock.calls[1][1].headers).get("X-Demo-Retailer")).toBe(
      "bhn",
    );
  });
});
