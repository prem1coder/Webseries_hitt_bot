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

    # Concurrency & Environment
    MAX_CONCURRENT_STREAMS: int = Field(default=20)
    ENVIRONMENT: str = Field(default="development")

    def validate_for_environment(self) -> None:
        """
        Enforce fail-fast validation for production deployments.
        In production, all credentials, IDs, and secrets must be safe, non-default, and non-empty.
        """
        env = (self.ENVIRONMENT or "development").strip().lower()
        if env != "production":
            return

        errors = []

        if not self.BOT_TOKEN or len(self.BOT_TOKEN) < 10 or ":" not in self.BOT_TOKEN:
            errors.append("Production requires a valid BOT_TOKEN from @BotFather.")

        if not self.TELEGRAM_API_ID or self.TELEGRAM_API_ID <= 0:
            errors.append("Production requires a valid positive numeric TELEGRAM_API_ID.")

        if not self.TELEGRAM_API_HASH or len(self.TELEGRAM_API_HASH) < 16:
            errors.append("Production requires a valid TELEGRAM_API_HASH.")

        # Channel IDs
        for ch_name, ch_val in [("ARCHIVE_CHANNEL_ID", self.ARCHIVE_CHANNEL_ID), ("MAIN_CHANNEL_ID", self.MAIN_CHANNEL_ID)]:
            if not ch_val:
                errors.append(f"Production requires {ch_name} to be set.")
            else:
                s_val = str(ch_val).strip()
                if s_val.startswith("http") or s_val.startswith("t.me"):
                    errors.append(f"Production requires {ch_name} to be a numeric Telegram channel ID, not an invite URL.")
                elif not (s_val.startswith("-") and s_val.lstrip("-").isdigit()):
                    errors.append(f"Production requires {ch_name} to be a numeric Telegram channel ID (e.g. -100xxxxxxxxxx).")

        # Database URL
        if not self.DATABASE_URL or "postgres:password@" in self.DATABASE_URL or "change_this_password" in self.DATABASE_URL:
            errors.append("Production requires a secure DATABASE_URL with non-default credentials.")

        # Download secret
        insecure_secrets = ["default_insecure_key_change_in_production", "super_secret", "change_me", "secret"]
        if not self.DOWNLOAD_SECRET or len(self.DOWNLOAD_SECRET) < 32 or any(sec in self.DOWNLOAD_SECRET.lower() for sec in insecure_secrets):
            errors.append("Production requires a strong, random DOWNLOAD_SECRET of at least 32 characters.")

        # Token expiry
        if self.TOKEN_EXPIRY_MINUTES < 1 or self.TOKEN_EXPIRY_MINUTES > 1440:
            errors.append("TOKEN_EXPIRY_MINUTES must be between 1 and 1440 minutes (24 hours).")

        if errors:
            raise ValueError(f"Production configuration validation failed:\n - " + "\n - ".join(errors))

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
