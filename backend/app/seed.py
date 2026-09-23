import argparse
import asyncio
import logging

from app.config import get_settings
from app.redis import RedisClient
from app.retailers import RETAILERS
from app.retrieval import CatalogService


async def run(*, reset: bool, count: int, migrate_legacy: bool) -> None:
    settings = get_settings()
    redis = RedisClient(settings)
    catalogs: list[CatalogService] = []
    try:
        if not await redis.ping():
            raise RuntimeError("Redis did not respond to PING")
        for retailer in RETAILERS.values():
            catalog = CatalogService(settings, redis.client, retailer)
            catalogs.append(catalog)
            if reset:
                await catalog.reset()
            if migrate_legacy:
                await catalog.cleanup_legacy_namespaces()
            document_count = await catalog.seed(
                retailer.generate_catalog(count),
                retailer.tenants(),
                retailer.profiles(),
                retailer.promotions(),
            )
            logging.info("Seeded %s %s catalog records", document_count, retailer.experience_name)
        await redis.initialize_runtime()
    finally:
        for catalog in catalogs:
            await catalog.close()
        await redis.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the configured retailer demo runtime")
    parser.add_argument(
        "--reset", action="store_true", help="Reset only namespaced demo catalog state"
    )
    parser.add_argument(
        "--count", type=int, default=360, help="Reserved catalog size for Milestone 1"
    )
    parser.add_argument(
        "--migrate-legacy",
        action="store_true",
        help="Remove pre-namespace-isolation demo state after the current retailer is reset",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run(reset=args.reset, count=args.count, migrate_legacy=args.migrate_legacy))


if __name__ == "__main__":
    main()
