from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    BigInteger, SmallInteger, Integer, String, Text, DateTime,
    ForeignKey, UniqueConstraint, CheckConstraint, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Content(Base):
    __tablename__ = "contents"
    __table_args__ = (
        CheckConstraint("content_type IN ('movie', 'series')", name="ck_contents_content_type"),
        UniqueConstraint("normalized_title", "content_type", "year", name="uq_contents_identity"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_title: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'movie' or 'series'
    year: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    original_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    poster_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    seasons: Mapped[List["Season"]] = relationship("Season", back_populates="content", cascade="all, delete-orphan", order_by="Season.season_number")
    files: Mapped[List["File"]] = relationship("File", back_populates="content", cascade="all, delete-orphan")


class Season(Base):
    __tablename__ = "seasons"
    __table_args__ = (
        UniqueConstraint("content_id", "season_number", name="uq_seasons_content_season"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    content_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False)
    season_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    content: Mapped["Content"] = relationship("Content", back_populates="seasons")
    episodes: Mapped[List["Episode"]] = relationship("Episode", back_populates="season", cascade="all, delete-orphan", order_by="Episode.episode_number")


class Episode(Base):
    __tablename__ = "episodes"
    __table_args__ = (
        UniqueConstraint("season_id", "episode_number", name="uq_episodes_season_episode"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    season_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False)
    episode_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    season: Mapped["Season"] = relationship("Season", back_populates="episodes")
    files: Mapped[List["File"]] = relationship("File", back_populates="episode", cascade="all, delete-orphan")


class File(Base):
    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint("telegram_channel_id", "telegram_message_id", name="uq_files_telegram_message"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    content_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False, index=True)
    episode_id: Mapped[Optional[int]] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True, index=True)
    quality: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    audio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    telegram_channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    telegram_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    content: Mapped["Content"] = relationship("Content", back_populates="files")
    episode: Mapped[Optional["Episode"]] = relationship("Episode", back_populates="files")
