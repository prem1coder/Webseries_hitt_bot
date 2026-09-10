import logging
from dataclasses import dataclass
from typing import Optional
from telethon.tl.types import (
    Message,
    DocumentAttributeFilename,
    DocumentAttributeVideo,
    DocumentAttributeAudio,
    MessageMediaDocument
)

logger = logging.getLogger(__name__)


@dataclass
class ExtractedMediaInfo:
    channel_id: int
    message_id: int
    file_name: str
    file_size_bytes: int
    duration_seconds: Optional[int] = None
    mime_type: Optional[str] = None
    media_type: str = "document"  # 'video', 'document', 'audio'


class TelegramMessageInspector:
    @staticmethod
    def inspect_message(channel_id: int, message: Message) -> Optional[ExtractedMediaInfo]:
        """
        Inspect a Telethon Message object and extract media details.
        Returns ExtractedMediaInfo if the message contains valid video/document media, else None.
        """
        if not message or not message.media:
            return None

        # Check if media is document / video
        if not isinstance(message.media, MessageMediaDocument):
            # Check if direct video attribute
            if not getattr(message.media, "document", None):
                return None

        document = getattr(message.media, "document", None)
        if not document:
            return None

        file_name: Optional[str] = None
        duration_seconds: Optional[int] = None
        media_type = "document"

        # Iterate over document attributes
        if hasattr(document, "attributes"):
            for attr in document.attributes:
                if isinstance(attr, DocumentAttributeFilename):
                    file_name = attr.file_name
                elif isinstance(attr, DocumentAttributeVideo):
                    duration_seconds = int(attr.duration)
                    media_type = "video"
                elif isinstance(attr, DocumentAttributeAudio):
                    if duration_seconds is None:
                        duration_seconds = int(attr.duration)
                    media_type = "audio"

        # Fallback 1: Check caption or message text for filename
        if not file_name:
            if message.message and len(message.message.strip()) > 0:
                first_line = message.message.strip().split("\n")[0].strip()
                if "." in first_line:
                    file_name = first_line

        # Fallback 2: Generate default filename
        if not file_name:
            mime_type = getattr(document, "mime_type", "video/mp4")
            ext = "mp4" if "mp4" in mime_type else "mkv"
            file_name = f"video_msg_{message.id}.{ext}"

        file_size = getattr(document, "size", 0)
        mime = getattr(document, "mime_type", None)

        return ExtractedMediaInfo(
            channel_id=channel_id,
            message_id=message.id,
            file_name=file_name,
            file_size_bytes=file_size,
            duration_seconds=duration_seconds,
            mime_type=mime,
            media_type=media_type
        )
