# Product Artwork

The Retail Showcase layout uses optional product images and a branded fallback.
Search ranking, embeddings, and Redis isolation do not depend on images.

## Imported Catalogs

Each product can include `"image_url": "https://..."` or `"image_url": null`.
The API validates HTTP(S) URLs, stores the value on the retailer's existing Redis
catalog hash, and returns it with search results. No image bytes are stored in Redis.
Existing catalogs without this field remain compatible and do not need reseeding.

The onboarding prompt requests only verified public product image URLs that accurately
represent the item. Synthetic items without suitable imagery should use null.
The browser loads images directly from their host, without a referrer. Missing,
invalid, or failed images display a clearly generic branded placeholder. URLs can
expire or be blocked by the image host; the layout remains usable in that case.

For repeated or externally distributed demos, use approved retailer assets hosted
on infrastructure you control, with appropriate usage permission. Public availability
alone does not grant redistribution rights. The application does not scrape or
download an image collection during onboarding.

## BHN Examples

Two existing BHN products use public GiftCards.com artwork as a display-only mapping.
This avoids rewriting the existing catalog and keeps imported retailer IDs isolated.
Source pages checked September 23, 2026:

- Starbucks: https://wakefern.giftcards.com/starbucks-egift
- AMC Theatres: https://wakefern.giftcards.com/amc-egift

The direct image URLs are recorded in `frontend/src/components/ProductArtwork.tsx`.
Other BHN cards use generic gift-card placeholders until approved artwork is supplied.

## Branding

The retailer is the primary identity. The footer reads **Made with RedisVL** with
red RedisVL lettering. No legacy stacked-block Redis logo is used. This is a text
credit, not a recreation of an official Redis logo asset.
