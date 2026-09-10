import asyncio
import logging
from database.config import get_settings
from database.connection import check_db_ready, dispose_engine
from indexer.telegram.client import start_telethon_client, stop_telethon_client
from indexer.services.indexer_service import IndexerService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("indexer")


async def main():
    settings = get_settings()
    settings.validate_for_environment()

    logger.info("Checking database readiness...")
    await check_db_ready()
    logger.info("Database schema and connectivity verified.")

    logger.info("Connecting to Telegram MTProto Client...")
    client = await start_telethon_client()

    indexer = IndexerService(client)
    try:
        await indexer.run_historical_crawl()
    finally:
        await stop_telethon_client()
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
