import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it } from "vitest";
import type { ProductResult } from "../api/search";
import { ProductArtwork } from "./ProductArtwork";

Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
const container = document.createElement("div");
let root = createRoot(container);
const product: ProductResult = {
  id: "gc_starbucks",
  brand_name: "Example Cooler",
  description: "An insulated cooler.",
  categories: ["Outdoors"],
  delivery_types: ["shipping"],
  min_denomination: 20,
  max_denomination: 80,
  promoted: false,
  score: null,
  score_breakdown: null,
};
afterEach(() => {
  act(() => root.unmount());
  root = createRoot(container);
});

describe("product artwork", () => {
  it("does not use BHN artwork for an imported retailer with a matching ID", () => {
    act(() =>
      root.render(
        <ProductArtwork product={product} retailerId="outdoor-store" />,
      ),
    );
    expect(container.querySelector("img")).toBeNull();
    expect(container.textContent).toContain("Example Cooler");
  });
  it("renders an uploaded URL and falls back if it fails", () => {
    act(() =>
      root.render(
        <ProductArtwork
          product={{ ...product, image_url: "https://example.com/cooler.png" }}
          retailerId="outdoor-store"
        />,
      ),
    );
    const image = container.querySelector("img")!;
    expect(image.src).toBe("https://example.com/cooler.png");
    act(() => image.dispatchEvent(new Event("error")));
    expect(container.querySelector("img")).toBeNull();
    expect(container.textContent).toContain("Product image unavailable");
  });
  it("rejects unsafe image schemes even in an older catalog", () => {
    act(() =>
      root.render(
        <ProductArtwork
          product={{ ...product, image_url: "javascript:alert(1)" }}
          retailerId="outdoor-store"
        />,
      ),
    );
    expect(container.querySelector("img")).toBeNull();
  });
});
