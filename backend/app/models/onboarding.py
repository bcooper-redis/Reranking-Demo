import re

from pydantic import BaseModel, Field, HttpUrl, model_validator


class ImportedTheme(BaseModel):
    accent: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    accent_strong: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    accent_soft: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    canvas: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class ImportedProduct(BaseModel):
    brand_name: str = Field(min_length=2, max_length=140)
    image_url: HttpUrl | None = None
    description: str = Field(min_length=12, max_length=700)
    aliases: list[str] = Field(default_factory=list, max_length=12)
    categories: list[str] = Field(min_length=1, max_length=6)
    recipient_tags: list[str] = Field(default_factory=lambda: ["shopper"], max_length=8)
    delivery_types: list[str] = Field(default_factory=lambda: ["shipping"], max_length=3)
    min_price: int = Field(default=10, ge=1, le=5_000)
    max_price: int = Field(default=100, ge=1, le=5_000)

    @model_validator(mode="after")
    def validate_price_range(self) -> "ImportedProduct":
        if self.max_price < self.min_price:
            raise ValueError("max_price must be greater than or equal to min_price")
        return self


class ImportedDemoPaths(BaseModel):
    customer_query: str = Field(min_length=3, max_length=180)
    exact_product_query: str = Field(min_length=2, max_length=140)
    preference_query: str = Field(min_length=3, max_length=180)
    preference_profile_name: str = Field(min_length=2, max_length=80)
    preference_category: str = Field(min_length=2, max_length=80)
    prefix_query: str | None = Field(
        default=None, min_length=2, max_length=24, pattern=r"^[A-Za-z0-9]+$"
    )
    prefix_expected_product: str | None = Field(default=None, min_length=2, max_length=140)


class RetailerPayload(BaseModel):
    organization_name: str = Field(min_length=2, max_length=120)
    experience_name: str = Field(min_length=2, max_length=80)
    catalog_label: str = Field(default="products", min_length=2, max_length=40)
    theme: ImportedTheme
    demo_paths: ImportedDemoPaths | None = None
    products: list[ImportedProduct] = Field(min_length=3, max_length=360)


class RetailerImportRequest(RetailerPayload):
    @model_validator(mode="after")
    def validate_catalog_size(self) -> "RetailerImportRequest":
        if len(self.products) != 360:
            raise ValueError("products must contain exactly 360 items")
        if self.demo_paths:
            if not (
                self.demo_paths.prefix_query and self.demo_paths.prefix_expected_product
            ):
                raise ValueError(
                    "demo_paths must include prefix_query and prefix_expected_product"
                )
            categories = {
                category for product in self.products for category in product.categories
            }
            if self.demo_paths.preference_category not in categories:
                raise ValueError(
                    "demo_paths.preference_category must exactly match a product category"
                )
            self._validate_prefix_demo()
        return self

    def _validate_prefix_demo(self) -> None:
        assert self.demo_paths is not None
        assert self.demo_paths.prefix_query is not None
        assert self.demo_paths.prefix_expected_product is not None
        prefix = self.demo_paths.prefix_query.lower()
        target = next(
            (
                product
                for product in self.products
                if product.brand_name.casefold()
                == self.demo_paths.prefix_expected_product.casefold()
            ),
            None,
        )
        if target is None:
            raise ValueError(
                "demo_paths.prefix_expected_product must exactly match a product name"
            )
        if not any(
            value.casefold().startswith(prefix)
            for value in [target.brand_name, *target.aliases]
        ):
            raise ValueError(
                "demo_paths.prefix_query must be a prefix of the expected product name or alias"
            )
        if prefix in _search_terms(target):
            raise ValueError(
                "the expected prefix product must not match prefix_query as a whole text term"
            )
        if not any(
            product is not target and prefix in _search_terms(product)
            for product in self.products
        ):
            raise ValueError(
                "prefix_query needs another catalog product with a literal text match"
            )


def _search_terms(product: ImportedProduct) -> set[str]:
    values = [
        product.brand_name,
        product.description,
        *product.aliases,
        *product.categories,
        *product.recipient_tags,
    ]
    return {
        term.casefold()
        for value in values
        for term in re.findall(r"[A-Za-z0-9]+", value)
    }


class StoredRetailerPayload(RetailerPayload):
    """A compatibility model for Foundry catalogs saved before the 360-product standard."""


class RetailerImportResponse(BaseModel):
    retailer_id: str
    organization_name: str
    experience_name: str
    catalog_count: int
    index_alias: str


class RetailerDeleteResponse(BaseModel):
    retailer_id: str
