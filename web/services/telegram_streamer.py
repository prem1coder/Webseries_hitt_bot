import asyncio
import logging
from typing import AsyncGenerator, Optional
from database.config import get_settings
from indexer.telegram.client import get_telethon_client

logger = logging.getLogger(__name__)


class TelegramStreamer:
    _semaphore: Optional[asyncio.Semaphore] = None

    @classmethod
    def get_semaphore(cls) -> asyncio.Semaphore:
        """Get or initialize concurrency semaphore bounded by MAX_CONCURRENT_STREAMS."""
        if cls._semaphore is None:
            settings = get_settings()
            cls._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_STREAMS)
        return cls._semaphore

    @classmethod
    async def stream_media_chunks(
        cls,
        channel_id: int,
        message_id: int,
        offset_bytes: int = 0,
        chunk_size: int = 1024 * 1024  # 1MB chunks
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream media directly from Telegram MTProto servers chunk-by-chunk using a dedicated web session.
        Protected by a concurrency semaphore to prevent VPS resource exhaustion.
        """
        settings = get_settings()
        client = get_telethon_client(settings.TELEGRAM_STREAM_SESSION_NAME)
        if not client.is_connected():
            await client.connect()

        if not await client.is_user_authorized():
            logger.error(f"Stream session '{settings.TELEGRAM_STREAM_SESSION_NAME}' is not authorized.")
            raise RuntimeError(f"Web streaming session '{settings.TELEGRAM_STREAM_SESSION_NAME}' is not authorized.")

        sem = cls.get_semaphore()
        acquired = False
        try:
            await asyncio.wait_for(sem.acquire(), timeout=5.0)
            acquired = True
        except asyncio.TimeoutError:
            logger.error("Streaming capacity saturated (max concurrent streams reached).")
            raise RuntimeError("Streaming concurrency limit reached. Server busy.")

        try:
            entity = await client.get_entity(channel_id)
            message = await client.get_messages(entity, ids=message_id)

            if not message or not message.media:
                logger.error(f"No media found in message {channel_id}:{message_id}")
                return

            # Stream chunks directly from Telethon MTProto
            async for chunk in client.iter_download(
                message.media,
                offset=offset_bytes,
                chunk_size=chunk_size,
                request_size=chunk_size
            ):
                yield chunk

        except Exception as e:
            logger.error(f"Error streaming message {channel_id}:{message_id} from Telegram: {e}")
            raise
        finally:
            if acquired:
                sem.release()
