import asyncio
import logging
from database.connection import init_db
from indexer.telegram.client import start_telethon_client, stop_telethon_client
from indexer.services.indexer_service import IndexerService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("indexer")


async def main():
    logger.info("Initializing database schema...")
    await init_db()

    logger.info("Connecting to Telegram MTProto Client...")
    client = await start_telethon_client()

    indexer = IndexerService(client)
    try:
        await indexer.run_historical_crawl()
    finally:
        await stop_telethon_client()


if __name__ == "__main__":
    asyncio.run(main())
