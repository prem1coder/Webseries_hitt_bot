import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telethon.tl.types import (
    Message,
    MessageMediaDocument,
    Document,
    DocumentAttributeFilename,
    DocumentAttributeVideo,
    DocumentAttributeAudio,
)

from indexer.telegram.inspector import TelegramMessageInspector
from indexer.parser.filename_parser import FilenameParser
from database.connection import get_db_session, init_db
from database.repositories.content_repo import ContentRepository
from database.repositories.file_repo import FileRepository
from indexer.services.indexer_service import IndexerService
from bot.handlers.callbacks import _parse_callback_id, handle_file_selection


# ==============================================================================
# 1. Indexer Inspector Tests
# ==============================================================================

def test_inspector_accepts_valid_video():
    msg = MagicMock(spec=Message)
    doc = MagicMock(spec=Document)
    doc.size = 500000000
    doc.mime_type = "video/mp4"
    doc.attributes = [
        DocumentAttributeFilename(file_name="Inception.2010.1080p.mp4"),
        DocumentAttributeVideo(duration=8880, w=1920, h=1080)
    ]
    media = MagicMock(spec=MessageMediaDocument)
    media.document = doc
    msg.media = media
    msg.message = "Some caption"
    msg.id = 101

    info = TelegramMessageInspector.inspect_message(channel_id=-1001234567890, message=msg)
    assert info is not None
    assert info.file_name == "Inception.2010.1080p.mp4"
    assert info.file_size_bytes == 500000000
    assert info.duration_seconds == 8880
    assert info.media_type == "video"


def test_inspector_rejects_audio_only():
    msg = MagicMock(spec=Message)
    doc = MagicMock(spec=Document)
    doc.size = 10000000
    doc.mime_type = "audio/mpeg"
    doc.attributes = [
        DocumentAttributeFilename(file_name="podcast_ep1.mp3"),
        DocumentAttributeAudio(duration=1800, title="Podcast", performer="Host")
    ]
    media = MagicMock(spec=MessageMediaDocument)
    media.document = doc
    msg.media = media
    msg.id = 102

    info = TelegramMessageInspector.inspect_message(channel_id=-1001234567890, message=msg)
    assert info is None


def test_inspector_rejects_unsupported_documents():
    msg = MagicMock(spec=Message)
    doc = MagicMock(spec=Document)
    doc.size = 2000000
    doc.mime_type = "application/pdf"
    doc.attributes = [
        DocumentAttributeFilename(file_name="document.pdf")
    ]
    media = MagicMock(spec=MessageMediaDocument)
    media.document = doc
    msg.media = media
    msg.id = 103

    assert TelegramMessageInspector.inspect_message(channel_id=-1001234567890, message=msg) is None


def test_inspector_rejects_missing_filename_without_valid_caption():
    msg = MagicMock(spec=Message)
    doc = MagicMock(spec=Document)
    doc.size = 50000000
    doc.mime_type = "video/mp4"
    doc.attributes = []  # No filename attribute
    media = MagicMock(spec=MessageMediaDocument)
    media.document = doc
    msg.media = media
    msg.message = "Check out this cool clip without any extension!"
    msg.id = 104

    # Must NOT fabricate video_msg_104.mp4
    assert TelegramMessageInspector.inspect_message(channel_id=-1001234567890, message=msg) is None


def test_inspector_caption_fallback_with_video_extension():
    msg = MagicMock(spec=Message)
    doc = MagicMock(spec=Document)
    doc.size = 50000000
    doc.mime_type = "video/mp4"
    doc.attributes = []
    media = MagicMock(spec=MessageMediaDocument)
    media.document = doc
    msg.media = media
    msg.message = "Loki.S02E01.720p.WEB-DL.mkv\nEnjoy watching!"
    msg.id = 105

    info = TelegramMessageInspector.inspect_message(channel_id=-1001234567890, message=msg)
    assert info is not None
    assert info.file_name == "Loki.S02E01.720p.WEB-DL.mkv"


# ==============================================================================
# 2. Filename Parser Fixtures & Policy Tests
# ==============================================================================

def test_parser_preserves_title_casing():
    """Ensure titles like 'iPhone' and 'IMDb' are not damaged by title formatting."""
    parsed1 = FilenameParser.parse("iPhone.Photography.Masterclass.2023.1080p.mp4")
    assert "iPhone" in parsed1.title
    assert parsed1.normalized_title == "iphone photography masterclass"

    parsed2 = FilenameParser.parse("IMDb.Top.Rated.Movie.2022.720p.mkv")
    assert "IMDb" in parsed2.title
    assert parsed2.normalized_title == "imdb top rated movie"


def test_parser_ambiguous_seasonless_episode():
    """Policy test: single-season conventions assign Season 1 to 'Episode 05'."""
    parsed = FilenameParser.parse("Mirzapur.Episode.05.Hindi.720p.mkv")
    assert parsed.content_type == "series"
    assert parsed.season_number == 1
    assert parsed.episode_number == 5


def test_parser_season_pack_without_episodes():
    """Ensure season packs without episode numbers are detected with episode_number=None."""
    parsed = FilenameParser.parse("Game.of.Thrones.Season.1.Complete.720p.x264")
    assert parsed.content_type == "series"
    assert parsed.season_number == 1
    assert parsed.episode_number is None


# ==============================================================================
# 3. Callback Safety Tests
# ==============================================================================

def test_parse_callback_id_defensive():
    assert _parse_callback_id("content:42", "content") == 42
    assert _parse_callback_id("content:not_an_int", "content") is None
    assert _parse_callback_id("content:-5", "content") is None
    assert _parse_callback_id("wrong_prefix:42", "content") is None
    assert _parse_callback_id("", "content") is None
    assert _parse_callback_id(None, "content") is None


# ==============================================================================
# 4. Indexer Idempotency Tests
# ==============================================================================

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from database.models import Base


@pytest.mark.asyncio
async def test_indexer_idempotency_duplicate_message():
    """Process the exact same Telegram message twice and assert no duplicate DB entities."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    msg = MagicMock(spec=Message)
    doc = MagicMock(spec=Document)
    doc.size = 104857600
    doc.mime_type = "video/mp4"
    doc.attributes = [
        DocumentAttributeFilename(file_name="Breaking.Bad.S01E01.720p.mp4"),
        DocumentAttributeVideo(duration=3480, w=1280, h=720)
    ]
    media = MagicMock(spec=MessageMediaDocument)
    media.document = doc
    msg.media = media
    msg.message = ""
    msg.id = 999

    client_mock = MagicMock()
    service = IndexerService(client_mock)

    try:
        async with session_factory() as session:
            content_repo = ContentRepository(session)
            file_repo = FileRepository(session)

            # First pass
            file_id_1 = await service.index_single_message(
                channel_id=-1009999999999,
                message=msg,
                content_repo=content_repo,
                file_repo=file_repo
            )
            assert file_id_1 is not None

            # Second pass (exact duplicate message)
            file_id_2 = await service.index_single_message(
                channel_id=-1009999999999,
                message=msg,
                content_repo=content_repo,
                file_repo=file_repo
            )
            assert file_id_2 == file_id_1

            # Check count in DB
            contents = await content_repo.search_by_title("Breaking Bad")
            assert len(contents) == 1
            seasons = await content_repo.get_series_seasons(contents[0].id)
            assert len(seasons) == 1
            episodes = await content_repo.get_season_episodes(seasons[0].id)
            assert len(episodes) == 1
            qualities = await content_repo.get_episode_qualities(episodes[0].id)
            assert len(qualities) == 1
    finally:
        await engine.dispose()
