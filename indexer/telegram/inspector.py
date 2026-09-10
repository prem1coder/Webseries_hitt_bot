import logging
import os
from dataclasses import dataclass
from typing import Optional, Set
from telethon.tl.types import (
    Message,
    DocumentAttributeFilename,
    DocumentAttributeVideo,
    DocumentAttributeAudio,
    MessageMediaDocument
)

logger = logging.getLogger(__name__)

SUPPORTED_VIDEO_EXTENSIONS: Set[str] = {
    ".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv", ".wmv", ".m4v", ".ts"
}


@dataclass
class ExtractedMediaInfo:
    channel_id: int
    message_id: int
    file_name: str
    file_size_bytes: int
    duration_seconds: Optional[int] = None
    mime_type: Optional[str] = None
    media_type: str = "video"


class TelegramMessageInspector:
    @staticmethod
    def inspect_message(channel_id: int, message: Message) -> Optional[ExtractedMediaInfo]:
        """
        Inspect a Telethon Message object and extract media details.
        Accepts actual video media only.
        Rejects audio-only, images, photos, and unsupported documents.
        Returns None if message is not video or if a reliable filename cannot be extracted.
        """
        if not message or not message.media:
            return None

        # Check if media is a document
        if not isinstance(message.media, MessageMediaDocument):
            if not getattr(message.media, "document", None):
                return None

        document = getattr(message.media, "document", None)
        if not document:
            return None

        file_size = getattr(document, "size", 0)
        if not file_size or file_size <= 0:
            return None

        mime = getattr(document, "mime_type", None) or ""
        mime_lower = mime.lower()

        # Reject audio or image MIME types immediately
        if mime_lower.startswith("audio/") or mime_lower.startswith("image/"):
            logger.debug(f"Skipping message {message.id}: audio/image MIME type ({mime})")
            return None

        file_name: Optional[str] = None
        duration_seconds: Optional[int] = None
        has_video_attr = False
        has_audio_attr = False

        # Iterate over document attributes
        if hasattr(document, "attributes") and document.attributes:
            for attr in document.attributes:
                if isinstance(attr, DocumentAttributeFilename):
                    if attr.file_name and attr.file_name.strip():
                        file_name = attr.file_name.strip()
                elif isinstance(attr, DocumentAttributeVideo):
                    has_video_attr = True
                    duration_seconds = int(getattr(attr, "duration", 0) or 0)
                elif isinstance(attr, DocumentAttributeAudio):
                    has_audio_attr = True

        # Reject audio-only documents
        if has_audio_attr and not has_video_attr:
            logger.debug(f"Skipping message {message.id}: Document has audio attribute without video")
            return None

        # Fallback: Extract filename from caption/message text if not present in attributes
        if not file_name and message.message:
            candidate = message.message.strip().split("\n")[0].strip()
            _, ext = os.path.splitext(candidate)
            if ext.lower() in SUPPORTED_VIDEO_EXTENSIONS:
                file_name = candidate

        # If a reliable filename cannot be extracted, skip rather than fabricating one
        if not file_name:
            logger.debug(f"Skipping message {message.id}: No reliable filename could be extracted")
            return None

        # Check extension of extracted filename
        _, ext = os.path.splitext(file_name)
        ext_lower = ext.lower()

        is_video_by_ext = ext_lower in SUPPORTED_VIDEO_EXTENSIONS
        is_video_by_mime = mime_lower.startswith("video/")
        
        # Must be verified as video either by video attribute, video mime, or supported video extension
        if not (has_video_attr or is_video_by_mime or is_video_by_ext):
            logger.debug(f"Skipping message {message.id}: Unsupported media format for file '{file_name}' ({mime})")
            return None

        # Explicitly reject known non-video extensions even if mime is generic
        if ext_lower in {".mp3", ".flac", ".wav", ".aac", ".ogg", ".pdf", ".txt", ".zip", ".rar", ".apk", ".exe", ".docx"}:
            logger.debug(f"Skipping message {message.id}: Rejected non-video extension '{ext_lower}'")
            return None

        return ExtractedMediaInfo(
            channel_id=channel_id,
            message_id=message.id,
            file_name=file_name,
            file_size_bytes=file_size,
            duration_seconds=duration_seconds,
            mime_type=mime or "video/mp4",
            media_type="video"
        )
