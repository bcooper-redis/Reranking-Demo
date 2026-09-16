import argparse
import asyncio
import logging

from app.config import get_settings
from app.data import generate_catalog, profiles, promotions, tenants
from app.redis import RedisClient
from app.retrieval import CatalogService


async def run(*, reset: bool, count: int) -> None:
    settings = get_settings()
    redis = RedisClient(settings)
    catalog: CatalogService | None = None
    try:
        if not await redis.ping():
            raise RuntimeError("Redis did not respond to PING")
        catalog = CatalogService(settings, redis.client)
        if reset:
            await catalog.reset()
        document_count = await catalog.seed(
            generate_catalog(count), tenants(), profiles(), promotions()
        )
        await redis.initialize_runtime()
        logging.info("Seeded %s GiftFind catalog records", document_count)
    finally:
        if catalog is not None:
            await catalog.close()
        await redis.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize GiftFind demo runtime")
    parser.add_argument(
        "--reset", action="store_true", help="Reset only namespaced demo catalog state"
    )
    parser.add_argument(
        "--count", type=int, default=360, help="Reserved catalog size for Milestone 1"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run(reset=args.reset, count=args.count))


if __name__ == "__main__":
    main()
