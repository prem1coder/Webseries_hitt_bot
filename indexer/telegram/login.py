import asyncio
import logging
from database.config import get_settings
from indexer.telegram.client import get_telethon_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main():
    settings = get_settings()
    logger.info("Initializing Telethon client for interactive authentication...")
    logger.info(f"API ID: {settings.TELEGRAM_API_ID}")
    logger.info(f"Session Name: {settings.TELEGRAM_SESSION_NAME}")

    client = get_telethon_client()
    await client.start()

    me = await client.get_me()
    logger.info(f"Successfully authenticated as: {me.first_name} (ID: {me.id}, Username: @{me.username})")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
