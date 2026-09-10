import asyncio
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from database.models import Base, Content, Season, Episode, File
from database.repositories.content_repo import ContentRepository
from database.repositories.file_repo import FileRepository


class TestSearchEngine(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Create an async SQLite in-memory database for testing
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_search_and_hierarchy_resolution(self):
        async with self.session_factory() as session:
            content_repo = ContentRepository(session)
            file_repo = FileRepository(session)

            # 1. Insert Movie
            movie = await content_repo.find_or_create_content(
                title="Inception",
                content_type="movie",
                year=2010
            )
            # Add 2 qualities for movie
            await file_repo.upsert_file(
                content_id=movie.id,
                telegram_channel_id=-100123,
                telegram_message_id=1,
                quality="720p",
                file_name="Inception.720p.mkv",
                file_size_bytes=1000000
            )
            await file_repo.upsert_file(
                content_id=movie.id,
                telegram_channel_id=-100123,
                telegram_message_id=2,
                quality="1080p",
                file_name="Inception.1080p.mkv",
                file_size_bytes=2000000
            )

            # 2. Insert Series
            series = await content_repo.find_or_create_content(
                title="Breaking Bad",
                content_type="series",
                year=2008
            )
            season1 = await content_repo.find_or_create_season(series.id, 1, "Season 1")
            ep1 = await content_repo.find_or_create_episode(season1.id, 1, "Pilot")
            ep2 = await content_repo.find_or_create_episode(season1.id, 2, "Cat's in the Bag")

            await file_repo.upsert_file(
                content_id=series.id,
                episode_id=ep1.id,
                telegram_channel_id=-100123,
                telegram_message_id=10,
                quality="720p",
                file_name="BB.S01E01.720p.mkv"
            )
            await file_repo.upsert_file(
                content_id=series.id,
                episode_id=ep1.id,
                telegram_channel_id=-100123,
                telegram_message_id=11,
                quality="1080p",
                file_name="BB.S01E01.1080p.mkv"
            )

            await session.commit()

        # 3. Test Search
        async with self.session_factory() as session:
            content_repo = ContentRepository(session)

            # Case-insensitive search
            results = await content_repo.search_by_title("INCEPTION")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].title, "Inception")
            self.assertEqual(results[0].content_type, "movie")

            # Check movie qualities
            movie_qualities = await content_repo.get_movie_qualities(results[0].id)
            self.assertEqual(len(movie_qualities), 2)
            qualities = [q.quality for q in movie_qualities]
            self.assertIn("720p", qualities)
            self.assertIn("1080p", qualities)

            # Search series
            series_results = await content_repo.search_by_title("breaking")
            self.assertEqual(len(series_results), 1)
            self.assertEqual(series_results[0].title, "Breaking Bad")
            self.assertEqual(series_results[0].content_type, "series")

            # Check series seasons
            seasons = await content_repo.get_series_seasons(series_results[0].id)
            self.assertEqual(len(seasons), 1)
            self.assertEqual(seasons[0].season_number, 1)

            # Check season episodes
            episodes = await content_repo.get_season_episodes(seasons[0].id)
            self.assertEqual(len(episodes), 2)

            # Check episode 1 qualities
            ep1_qualities = await content_repo.get_episode_qualities(episodes[0].id)
            self.assertEqual(len(ep1_qualities), 2)


if __name__ == "__main__":
    unittest.main()
