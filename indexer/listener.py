import asyncio
import logging
from telethon import TelegramClient, events
from telethon.tl.types import Message

from database.config import get_settings
from database.connection import get_db_session, check_db_ready, dispose_engine
from database.repositories.content_repo import ContentRepository
from database.repositories.file_repo import FileRepository
from indexer.telegram.client import start_telethon_client, stop_telethon_client
from indexer.services.indexer_service import IndexerService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("listener")
settings = get_settings()


async def register_listener(client: TelegramClient):
    """Register event handler for new messages in the archive channel."""
    target_channel = settings.ARCHIVE_CHANNEL_ID
    logger.info(f"Setting up real-time upload listener on channel: {target_channel}...")

    try:
        lookup_channel = target_channel
        if isinstance(target_channel, str) and (target_channel.lstrip("-").isdigit()):
            lookup_channel = int(target_channel)

        entity = await client.get_entity(lookup_channel)
        channel_id = getattr(entity, "id", None)
        if channel_id is None:
            raise ValueError(f"Resolved entity has no ID: {entity}")

        channel_id_str = str(channel_id)
        if not channel_id_str.startswith("-100"):
            channel_id = int(f"-100{abs(int(channel_id))}")
        else:
            channel_id = int(channel_id)
        logger.info(f"Successfully resolved canonical archive channel ID: {channel_id}")
    except Exception as e:
        logger.critical(f"Failed to resolve archive channel entity for '{target_channel}': {e}. Hard failing listener startup.")
        raise RuntimeError(f"Cannot start listener: archive channel '{target_channel}' could not be resolved.") from e

    indexer_service = IndexerService(client)

    @client.on(events.NewMessage(chats=channel_id))
    async def handler(event: events.NewMessage.Event):
        message: Message = event.message
        raw_chat_id = event.chat_id or channel_id
        # Canonical -100 ID
        if not str(raw_chat_id).startswith("-100"):
            canonical_id = int(f"-100{abs(int(raw_chat_id))}")
        else:
            canonical_id = int(raw_chat_id)

        logger.info(f"New message received in archive channel {canonical_id} (ID: {message.id}). Inspecting...")

        try:
            async with get_db_session() as session:
                content_repo = ContentRepository(session)
                file_repo = FileRepository(session)

                file_id = await indexer_service.index_single_message(
                    channel_id=canonical_id,
                    message=message,
                    content_repo=content_repo,
                    file_repo=file_repo
                )

                if file_id:
                    logger.info(f"✅ Real-time index complete for message {message.id} -> File ID {file_id}")
                else:
                    logger.debug(f"Message {message.id} contained no indexable video media.")

        except Exception as e:
            logger.error(f"Error in real-time indexer for message {message.id}: {e}", exc_info=True)

    logger.info("Real-time upload listener is active and waiting for new channel uploads.")


async def main():
    settings.validate_for_environment()
    logger.info("Checking database readiness...")
    if not await check_db_ready():
        logger.critical("Database is not ready. Failing listener startup.")
        raise RuntimeError("Database readiness check failed on listener startup.")

    logger.info("Starting Telethon client...")
    client = await start_telethon_client()

    await register_listener(client)

    try:
        logger.info("Running listener loop...")
        await client.run_until_disconnected()
    finally:
        await stop_telethon_client()
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
