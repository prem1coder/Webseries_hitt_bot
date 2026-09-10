from typing import Optional, List, Tuple
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import File, Content, Episode, Season


class FileRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, file_id: int) -> Optional[File]:
        """Fetch file by ID with associated content and episode details."""
        stmt = (
            select(File)
            .options(
                selectinload(File.content),
                selectinload(File.episode).selectinload(Episode.season)
            )
            .where(File.id == file_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_telegram_message(self, channel_id: int, message_id: int) -> Optional[File]:
        """Fetch file by unique Telegram channel and message reference."""
        stmt = select(File).where(
            and_(
                File.telegram_channel_id == channel_id,
                File.telegram_message_id == message_id
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_file(
        self,
        content_id: int,
        telegram_channel_id: int,
        telegram_message_id: int,
        episode_id: Optional[int] = None,
        quality: Optional[str] = None,
        file_name: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
        duration_seconds: Optional[int] = None,
        audio: Optional[str] = None
    ) -> Tuple[File, bool]:
        """Insert or update file record with duplicate protection."""
        existing = await self.get_by_telegram_message(telegram_channel_id, telegram_message_id)
        if existing:
            # Update metadata if missing
            existing.quality = quality or existing.quality
            existing.file_name = file_name or existing.file_name
            existing.file_size_bytes = file_size_bytes or existing.file_size_bytes
            existing.duration_seconds = duration_seconds or existing.duration_seconds
            existing.audio = audio or existing.audio
            return existing, False

        new_file = File(
            content_id=content_id,
            episode_id=episode_id,
            quality=quality,
            file_name=file_name,
            file_size_bytes=file_size_bytes,
            duration_seconds=duration_seconds,
            audio=audio,
            telegram_channel_id=telegram_channel_id,
            telegram_message_id=telegram_message_id
        )
        self.session.add(new_file)
        await self.session.flush()
        return new_file, True
