import os
from typing import Union
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # Telegram Bot API
    BOT_TOKEN: str = Field(default="")

    # Telegram MTProto (Telethon)
    TELEGRAM_API_ID: int = Field(default=0)
    TELEGRAM_API_HASH: str = Field(default="")
    TELEGRAM_SESSION_NAME: str = Field(default="archive_indexer")
    TELEGRAM_STREAM_SESSION_NAME: str = Field(default="stream_service")

    # Channels
    ARCHIVE_CHANNEL_ID: Union[int, str] = Field(default="")
    MAIN_CHANNEL_ID: Union[int, str] = Field(default="")
    MAIN_CHANNEL_INVITE_LINK: str = Field(default="https://t.me/your_channel_invite")

    # Database
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:password@localhost:5432/video_bot")
    POSTGRES_DB: str = Field(default="video_bot")
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(default="password")

    # Security & Tokens
    DOWNLOAD_SECRET: str = Field(default="default_insecure_key_change_in_production")
    TOKEN_EXPIRY_MINUTES: int = Field(default=15)

    # Web Server
    DOMAIN: str = Field(default="localhost:8000")
    WEB_HOST: str = Field(default="0.0.0.0")
    WEB_PORT: int = Field(default=8000)
    USE_HTTPS: bool = Field(default=False)

    # Indexer
    BATCH_SIZE: int = Field(default=100)
    FLOOD_WAIT_MAX_RETRIES: int = Field(default=5)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def base_web_url(self) -> str:
        protocol = "https" if self.USE_HTTPS else "http"
        return f"{protocol}://{self.DOMAIN}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
