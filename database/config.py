import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # Telegram Bot API
    BOT_TOKEN: str = Field(default="123456789:ABCDefghIJKlmnoPQRstuvWXYZ")

    # Telegram MTProto (Telethon)
    TELEGRAM_API_ID: int = Field(default=12345678)
    TELEGRAM_API_HASH: str = Field(default="0123456789abcdef0123456789abcdef")
    TELEGRAM_SESSION_NAME: str = Field(default="archive_indexer")

    # Channels
    ARCHIVE_CHANNEL_ID: int = Field(default=-1001234567890)
    MAIN_CHANNEL_ID: int = Field(default=-1009876543210)
    MAIN_CHANNEL_INVITE_LINK: str = Field(default="https://t.me/your_channel_invite")

    # Database
    DATABASE_URL: str = Field(default="postgresql+asyncpg://video_admin:change_this_password@localhost:5432/video_bot")
    POSTGRES_DB: str = Field(default="video_bot")
    POSTGRES_USER: str = Field(default="video_admin")
    POSTGRES_PASSWORD: str = Field(default="change_this_password")

    # Security & Tokens
    DOWNLOAD_SECRET: str = Field(default="super_secret_signing_key_for_video_download_tokens_2026")
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
