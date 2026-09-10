from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Content, Season, Episode, File


class ContentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def normalize_title(title: str) -> str:
        """Normalize title for consistent matching: lowercase, alphanumeric and single spaces."""
        import re
        cleaned = re.sub(r"[^\w\s]", " ", title.lower())
        return re.sub(r"\s+", " ", cleaned).strip()

    async def get_by_id(self, content_id: int) -> Optional[Content]:
        """Fetch content by ID."""
        stmt = select(Content).where(Content.id == content_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_by_title(self, query: str, limit: int = 20) -> List[Content]:
        """Search contents using normalized title substring or exact matching."""
        norm_query = self.normalize_title(query)
        if not norm_query:
            return []

        stmt = (
            select(Content)
            .where(Content.normalized_title.ilike(f"%{norm_query}%"))
            .order_by(
                # Exact match first, then alphabetically
                (Content.normalized_title == norm_query).desc(),
                Content.title.asc()
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_movie_qualities(self, content_id: int) -> List[File]:
        """Fetch all available quality files for a movie."""
        stmt = (
            select(File)
            .where(
                and_(
                    File.content_id == content_id,
                    File.episode_id.is_(None)
                )
            )
            .order_by(File.quality.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_series_seasons(self, content_id: int) -> List[Season]:
        """Fetch all seasons for a series."""
        stmt = (
            select(Season)
            .where(Season.content_id == content_id)
            .order_by(Season.season_number.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_season_by_id(self, season_id: int) -> Optional[Season]:
        """Fetch season by ID."""
        stmt = select(Season).where(Season.id == season_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_season_episodes(self, season_id: int) -> List[Episode]:
        """Fetch all episodes for a season."""
        stmt = (
            select(Episode)
            .where(Episode.season_id == season_id)
            .order_by(Episode.episode_number.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_episode_by_id(self, episode_id: int) -> Optional[Episode]:
        """Fetch episode by ID with its season and content."""
        stmt = (
            select(Episode)
            .options(selectinload(Episode.season).selectinload(Season.content))
            .where(Episode.id == episode_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_episode_qualities(self, episode_id: int) -> List[File]:
        """Fetch all available quality files for an episode."""
        stmt = (
            select(File)
            .where(File.episode_id == episode_id)
            .order_by(File.quality.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_or_create_content(
        self,
        title: str,
        content_type: str,
        year: Optional[int] = None,
        original_title: Optional[str] = None,
        poster_url: Optional[str] = None,
        description: Optional[str] = None
    ) -> Content:
        """Find existing content by normalized title & type & year, or create new."""
        norm_title = self.normalize_title(title)
        stmt = select(Content).where(
            and_(
                Content.normalized_title == norm_title,
                Content.content_type == content_type
            )
        )
        if year is not None:
            stmt = stmt.where(Content.year == year)

        result = await self.session.execute(stmt)
        content = result.scalar_one_or_none()

        if not content:
            content = Content(
                title=title,
                normalized_title=norm_title,
                content_type=content_type,
                year=year,
                original_title=original_title or title,
                poster_url=poster_url,
                description=description
            )
            self.session.add(content)
            await self.session.flush()

        return content

    async def find_or_create_season(
        self,
        content_id: int,
        season_number: int,
        title: Optional[str] = None
    ) -> Season:
        """Find existing season or create new."""
        stmt = select(Season).where(
            and_(
                Season.content_id == content_id,
                Season.season_number == season_number
            )
        )
        result = await self.session.execute(stmt)
        season = result.scalar_one_or_none()

        if not season:
            season = Season(
                content_id=content_id,
                season_number=season_number,
                title=title or f"Season {season_number}"
            )
            self.session.add(season)
            await self.session.flush()

        return season

    async def find_or_create_episode(
        self,
        season_id: int,
        episode_number: int,
        title: Optional[str] = None,
        duration_seconds: Optional[int] = None
    ) -> Episode:
        """Find existing episode or create new."""
        stmt = select(Episode).where(
            and_(
                Episode.season_id == season_id,
                Episode.episode_number == episode_number
            )
        )
        result = await self.session.execute(stmt)
        episode = result.scalar_one_or_none()

        if not episode:
            ep_title = title or f"Episode {episode_number}"
            episode = Episode(
                season_id=season_id,
                episode_number=episode_number,
                title=ep_title,
                normalized_title=self.normalize_title(ep_title),
                duration_seconds=duration_seconds
            )
            self.session.add(episode)
            await self.session.flush()

        return episode
