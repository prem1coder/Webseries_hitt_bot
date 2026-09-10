import logging
from typing import Optional, Dict
from telethon import TelegramClient
from database.config import get_settings

logger = logging.getLogger(__name__)

_telethon_clients: Dict[str, TelegramClient] = {}


def get_telethon_client(session_name: Optional[str] = None) -> TelegramClient:
    """Get or create Telethon client instance for the given session name."""
    settings = get_settings()
    session = session_name or settings.TELEGRAM_SESSION_NAME

    if session not in _telethon_clients:
        _telethon_clients[session] = TelegramClient(
            session,
            settings.TELEGRAM_API_ID,
            settings.TELEGRAM_API_HASH
        )
    return _telethon_clients[session]


async def start_telethon_client(session_name: Optional[str] = None, require_authorized: bool = True) -> TelegramClient:
    """Connect and start the Telethon client for the given session."""
    client = get_telethon_client(session_name)
    if not client.is_connected():
        await client.connect()
    
    if require_authorized and not await client.is_user_authorized():
        err_msg = (
            f"Telethon client '{session_name or 'default'}' is not authorized! "
            "Please run the interactive login script once to authenticate before starting the service."
        )
        logger.error(err_msg)
        raise RuntimeError(err_msg)
    return client


async def stop_telethon_client(session_name: Optional[str] = None) -> None:
    """Disconnect Telethon client cleanly."""
    settings = get_settings()
    session = session_name or settings.TELEGRAM_SESSION_NAME

    if session in _telethon_clients:
        client = _telethon_clients[session]
        if client.is_connected():
            await client.disconnect()
            logger.info(f"Telethon client '{session}' disconnected.")
        del _telethon_clients[session]
