import asyncio
import logging
from typing import Optional, Dict
from telethon import TelegramClient, errors
from telethon.tl.types import Message

from database.config import get_settings
from database.connection import get_db_session
from database.repositories.content_repo import ContentRepository
from database.repositories.file_repo import FileRepository
from indexer.parser.filename_parser import FilenameParser
from indexer.telegram.inspector import TelegramMessageInspector

logger = logging.getLogger(__name__)
settings = get_settings()


class IndexerService:
    def __init__(self, client: TelegramClient):
        self.client = client
        self.settings = get_settings()

    async def index_single_message(
        self,
        channel_id: int,
        message: Message,
        content_repo: ContentRepository,
        file_repo: FileRepository
    ) -> Optional[int]:
        """
        Process a single message: inspect media -> parse filename -> upsert into database.
        Returns file_id if indexed, None if skipped or not a valid media item.
        """
        media_info = TelegramMessageInspector.inspect_message(channel_id, message)
        if not media_info:
            return None

        # Check if already indexed
        existing_file = await file_repo.get_by_telegram_message(channel_id, message.id)
        if existing_file:
            logger.debug(f"Message {channel_id}:{message.id} already indexed (file_id: {existing_file.id}).")
            return existing_file.id

        # Parse filename
        parsed = FilenameParser.parse(media_info.file_name)

        # 1. Find or create Content
        content = await content_repo.find_or_create_content(
            title=parsed.title,
            content_type=parsed.content_type,
            year=parsed.year
        )

        episode_id: Optional[int] = None

        # 2. If Series, only create Season and Episode when a real episode number was parsed
        if parsed.content_type == "series":
            if parsed.episode_number is None:
                logger.warning(
                    f"Skipping series file without parsed episode number (possible season pack/ambiguous): "
                    f"'{media_info.file_name}' (Msg: {channel_id}:{message.id})"
                )
                return None

            season_num = parsed.season_number or 1
            episode_num = parsed.episode_number

            season = await content_repo.find_or_create_season(
                content_id=content.id,
                season_number=season_num
            )

            episode = await content_repo.find_or_create_episode(
                season_id=season.id,
                episode_number=episode_num,
                title=parsed.episode_title,
                duration_seconds=media_info.duration_seconds
            )
            episode_id = episode.id

        # 3. Upsert File
        file_obj, created = await file_repo.upsert_file(
            content_id=content.id,
            telegram_channel_id=channel_id,
            telegram_message_id=message.id,
            episode_id=episode_id,
            quality=parsed.quality,
            file_name=media_info.file_name,
            file_size_bytes=media_info.file_size_bytes,
            duration_seconds=media_info.duration_seconds,
            audio=parsed.audio
        )

        action = "Created" if created else "Updated"
        logger.info(
            f"[{action}] '{parsed.title}' ({parsed.content_type.upper()}) | Quality: {parsed.quality} | "
            f"Msg: {channel_id}:{message.id} | File: {media_info.file_name}"
        )
        return file_obj.id

    async def run_historical_crawl(
        self,
        channel_id: Optional[int] = None,
        limit: Optional[int] = None,
        batch_size: int = 100
    ) -> Dict[str, int]:
        """
        Crawl historical messages from the private archive channel.
        Handles rate limits and batch commits safely.
        """
        target_channel = channel_id or self.settings.ARCHIVE_CHANNEL_ID
        logger.info(f"Starting historical archive crawl for channel: {target_channel}...")

        stats = {
            "scanned": 0,
            "indexed": 0,
            "skipped": 0,
            "errors": 0
        }

        try:
            lookup_channel = target_channel
            if isinstance(target_channel, str) and (target_channel.lstrip("-").isdigit()):
                lookup_channel = int(target_channel)

            entity = await self.client.get_entity(lookup_channel)
            actual_channel_id = getattr(entity, "id", lookup_channel)
            # Ensure proper channel ID format
            if hasattr(entity, "id") and not str(actual_channel_id).startswith("-100"):
                actual_channel_id = int(f"-100{actual_channel_id}")
        except Exception as e:
            logger.error(f"Failed to resolve archive channel entity '{target_channel}': {e}")
            raise

        current_batch_count = 0

        async with get_db_session() as session:
            content_repo = ContentRepository(session)
            file_repo = FileRepository(session)

            async for message in self.client.iter_messages(entity, limit=limit, reverse=True):
                stats["scanned"] += 1
                try:
                    file_id = await self.index_single_message(
                        channel_id=actual_channel_id,
                        message=message,
                        content_repo=content_repo,
                        file_repo=file_repo
                    )
                    if file_id:
                        stats["indexed"] += 1
                    else:
                        stats["skipped"] += 1

                    current_batch_count += 1
                    if current_batch_count >= batch_size:
                        await session.commit()
                        logger.info(
                            f"Batch committed: Scanned {stats['scanned']} | Indexed {stats['indexed']} | "
                            f"Skipped {stats['skipped']}"
                        )
                        current_batch_count = 0

                except errors.FloodWaitError as fwe:
                    logger.warning(f"Telegram FloodWait encountered! Sleeping for {fwe.seconds} seconds...")
                    await asyncio.sleep(fwe.seconds + 1)
                except Exception as e:
                    stats["errors"] += 1
                    logger.error(f"Error indexing message {message.id}: {e}", exc_info=False)

            # Commit any remaining items
            await session.commit()

        logger.info(
            f"Historical crawl completed: Scanned={stats['scanned']}, Indexed={stats['indexed']}, "
            f"Skipped={stats['skipped']}, Errors={stats['errors']}"
        )
        return stats
