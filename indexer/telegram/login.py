import asyncio
import logging
from database.config import get_settings
from indexer.telegram.client import get_telethon_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main():
    logger.info("Initializing Telethon client for interactive authentication...")

    client = get_telethon_client()
    await client.start()

    if await client.is_user_authorized():
        logger.info("Successfully authenticated Telethon session.")
    else:
        logger.error("Authentication failed or incomplete.")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
