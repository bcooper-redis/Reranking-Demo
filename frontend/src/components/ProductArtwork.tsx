import { useState } from "react";
import { Gift, Package } from "lucide-react";
import type { ProductResult } from "../api/search";

// GiftCards.com product artwork; sources are recorded in docs/product-images.md.
const BHN_ARTWORK: Record<string, string> = {
  gc_starbucks:
    "https://productimages.nimbledeals.com/gift_card_skin/3b056f535d9454d1b0ccca3bfc6b9_1782253734294",
  gc_amc:
    "https://productimages.nimbledeals.com/gift_card_skin/428763f52eec3433630a87365f6c7b_1762255739059",
};

export function ProductArtwork({
  product,
  retailerId,
}: {
  product: ProductResult;
  retailerId: string;
}) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  const supplied =
    product.image_url ||
    (retailerId === "bhn" ? BHN_ARTWORK[product.id] : undefined);
  const imageUrl =
    supplied && /^https?:\/\//i.test(supplied) ? supplied : undefined;
  const isGift = product.delivery_types.some((type) =>
    ["egift", "physical"].includes(type),
  );
  return (
    <div className={`product-artwork ${isGift ? "gift-artwork" : ""}`}>
      {imageUrl && failedUrl !== imageUrl ? (
        <img
          alt={product.brand_name}
          src={imageUrl}
          loading="lazy"
          decoding="async"
          referrerPolicy="no-referrer"
          onError={() => setFailedUrl(imageUrl)}
        />
      ) : (
        <div
          className={`product-placeholder ${isGift ? "gift-placeholder" : ""}`}
        >
          {isGift ? (
            <Gift aria-hidden="true" />
          ) : (
            <Package aria-hidden="true" />
          )}
          <span className="placeholder-category">
            {product.categories[0] || "Collection"}
          </span>
          <strong>{product.brand_name}</strong>
          <small>{isGift ? "Gift card" : "Product image unavailable"}</small>
        </div>
      )}
    </div>
  );
}
