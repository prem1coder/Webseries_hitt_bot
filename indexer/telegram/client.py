import logging
from typing import Optional
from telethon import TelegramClient
from database.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_telethon_client: Optional[TelegramClient] = None


def get_telethon_client() -> TelegramClient:
    """Get or create singleton Telethon client instance."""
    global _telethon_client
    if _telethon_client is None:
        _telethon_client = TelegramClient(
            settings.TELEGRAM_SESSION_NAME,
            settings.TELEGRAM_API_ID,
            settings.TELEGRAM_API_HASH
        )
    return _telethon_client


async def start_telethon_client() -> TelegramClient:
    """Connect and start the Telethon client."""
    client = get_telethon_client()
    if not client.is_connected():
        await client.connect()
        if not await client.is_user_authorized():
            logger.warning(
                "Telethon client is not authorized! Please run the interactive login script once to authenticate."
            )
    return client


async def stop_telethon_client() -> None:
    """Disconnect Telethon client cleanly."""
    global _telethon_client
    if _telethon_client and _telethon_client.is_connected():
        await _telethon_client.disconnect()
        logger.info("Telethon client disconnected.")
