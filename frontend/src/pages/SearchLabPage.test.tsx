import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getReadiness } from "../api/health";
import {
  getPublicConfig,
  getSearchSuggestions,
  getTelemetry,
  searchCatalog,
  type PublicConfig,
  type SearchResponse,
} from "../api/search";
import { SearchLabPage } from "./SearchLabPage";

vi.mock("../api/health");
vi.mock("../api/search");
Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });

const config: PublicConfig = {
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
  tenants: [
    {
      id: "general",
      display_name: "General",
      allowed_delivery_types: [],
      promotion_ids: [],
    },
  ],
  profiles: [],
  promotions: [],
  rerankers: [
    {
      id: "minilm_l6",
      display_name: "MiniLM",
      provider: "hf",
      model: "minilm",
    },
    {
      id: "tinybert_l2",
      display_name: "TinyBERT",
      provider: "hf",
      model: "tinybert",
    },
  ],
  modes: ["baseline", "hybrid", "reranked", "compare"],
  catalog_count: 360,
  disclaimer: "Synthetic demo data.",
};

let container: HTMLDivElement;
let root: Root;
const input = () =>
  container.querySelector<HTMLInputElement>('[role="combobox"]')!;
const submit = () =>
  container.querySelector<HTMLButtonElement>('button[type="submit"]')!;

function change(element: HTMLInputElement | HTMLSelectElement, value: string) {
  const prototype =
    element instanceof HTMLInputElement
      ? HTMLInputElement.prototype
      : HTMLSelectElement.prototype;
  Object.getOwnPropertyDescriptor(prototype, "value")!.set!.call(
    element,
    value,
  );
  element.dispatchEvent(
    new Event(element instanceof HTMLInputElement ? "input" : "change", {
      bubbles: true,
    }),
  );
}

async function showSuggestions() {
  const toggle =
    container.querySelectorAll<HTMLInputElement>('[role="switch"]')[1];
  if (!toggle.checked) await act(async () => toggle.click());
  await act(async () => change(input(), "Star"));
  await act(async () => vi.advanceTimersByTimeAsync(180));
  expect(container.querySelector('[role="option"]')?.textContent).toBe(
    "Starbucks eGift",
  );
}

beforeEach(async () => {
  vi.useFakeTimers();
  vi.resetAllMocks();
  vi.mocked(getReadiness).mockResolvedValue({
    status: "ready",
    redis: "connected",
    environment: "local",
  });
  vi.mocked(getPublicConfig).mockResolvedValue(config);
  vi.mocked(getSearchSuggestions).mockResolvedValue({
    query: "Star",
    suggestions: [{ id: "gc_starbucks", brand_name: "Starbucks eGift" }],
    redis_search_query: null,
  });
  vi.mocked(getTelemetry).mockRejectedValue(new Error("Telemetry unavailable"));
  vi.mocked(searchCatalog).mockImplementation(
    async (query, _tenant, _profile, _promotion, mode) => ({
      request_id: "test-search",
      query,
      mode: mode as SearchResponse["mode"],
      results: [],
      timings_ms: {},
      intent: null,
      action: null,
      redis_search_queries: [],
      diagnostics: null,
      fallbacks: [],
    }),
  );
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => root.render(<SearchLabPage />));
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  vi.useRealTimers();
});

describe("typeahead selection", () => {
  it("searches the selected full name on click, not the stale fragment", async () => {
    await showSuggestions();
    expect(searchCatalog).not.toHaveBeenCalled();
    await act(async () =>
      container.querySelector<HTMLButtonElement>('[role="option"]')!.click(),
    );
    expect(input().value).toBe("Starbucks eGift");
    expect(searchCatalog).toHaveBeenCalledExactlyOnceWith(
      "Starbucks eGift",
      "general",
      "anonymous",
      null,
      "baseline",
      "minilm_l6",
      false,
    );
    expect(container.querySelector('[role="listbox"]')).toBeNull();
    expect(getTelemetry).toHaveBeenCalledOnce();
  });

  it("searches once on ArrowDown + Enter and prevents the form's default submit", async () => {
    await showSuggestions();
    await act(async () =>
      input().dispatchEvent(
        new KeyboardEvent("keydown", {
          key: "ArrowDown",
          bubbles: true,
          cancelable: true,
        }),
      ),
    );
    const enter = new KeyboardEvent("keydown", {
      key: "Enter",
      bubbles: true,
      cancelable: true,
    });
    await act(async () => input().dispatchEvent(enter));
    expect(enter.defaultPrevented).toBe(true);
    expect(searchCatalog).toHaveBeenCalledTimes(1);
    expect(vi.mocked(searchCatalog).mock.calls[0][0]).toBe("Starbucks eGift");
  });

  it("preserves the active profile, reranker, mode, and prefix setting", async () => {
    await act(async () =>
      change(
        container.querySelector<HTMLSelectElement>(".retail-path select")!,
        "personalization",
      ),
    );
    await act(async () => submit().click());
    const next = [
      ...container.querySelectorAll<HTMLButtonElement>("button"),
    ].find((button) => button.textContent?.startsWith("Continue:"))!;
    await act(async () => next.click());
    await act(async () =>
      change(
        container.querySelector<HTMLSelectElement>(".retail-reranker select")!,
        "tinybert_l2",
      ),
    );
    await act(async () =>
      container.querySelector<HTMLInputElement>('[role="switch"]')!.click(),
    );
    vi.mocked(searchCatalog).mockClear();
    await showSuggestions();
    await act(async () =>
      container.querySelector<HTMLButtonElement>('[role="option"]')!.click(),
    );
    expect(searchCatalog).toHaveBeenCalledExactlyOnceWith(
      "Starbucks eGift",
      "general",
      "tech_buyer",
      null,
      "reranked",
      "tinybert_l2",
      true,
    );
  });

  it("blocks duplicate submission while searching and allows retry after an error", async () => {
    let rejectSearch!: (reason: Error) => void;
    vi.mocked(searchCatalog).mockReturnValueOnce(
      new Promise((_resolve, reject) => {
        rejectSearch = reject;
      }),
    );
    await showSuggestions();
    await act(async () => {
      container.querySelector<HTMLButtonElement>('[role="option"]')!.click();
      container
        .querySelector("form")!
        .dispatchEvent(
          new Event("submit", { bubbles: true, cancelable: true }),
        );
    });
    expect(searchCatalog).toHaveBeenCalledTimes(1);
    expect(input().disabled).toBe(true);
    await act(async () => rejectSearch(new Error("Search failed")));
    expect(container.querySelector('[role="alert"]')?.textContent).toContain(
      "search service is unavailable",
    );
    expect(input().disabled).toBe(false);
    await act(async () => submit().click());
    expect(searchCatalog).toHaveBeenCalledTimes(2);
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });

  it("keeps Escape dismiss-only and manual search available", async () => {
    await showSuggestions();
    await act(async () =>
      input().dispatchEvent(
        new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
      ),
    );
    expect(container.querySelector('[role="listbox"]')).toBeNull();
    expect(searchCatalog).not.toHaveBeenCalled();
    await act(async () => submit().click());
    expect(vi.mocked(searchCatalog).mock.calls[0][0]).toBe("Star");
  });
});
