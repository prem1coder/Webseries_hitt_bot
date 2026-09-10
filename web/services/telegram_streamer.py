import logging
from typing import AsyncGenerator, Optional
from telethon import TelegramClient
from telethon.tl.types import MessageMediaDocument
from indexer.telegram.client import get_telethon_client

logger = logging.getLogger(__name__)


class TelegramStreamer:
    @staticmethod
    async def stream_media_chunks(
        channel_id: int,
        message_id: int,
        offset_bytes: int = 0,
        chunk_size: int = 1024 * 1024  # 1MB chunks
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream media directly from Telegram MTProto servers chunk-by-chunk without saving to VPS disk.
        """
        client = get_telethon_client()
        if not client.is_connected():
            await client.connect()

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
