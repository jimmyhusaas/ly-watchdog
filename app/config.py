"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Values are read from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Meta
    environment: str = Field(default="development")
    app_name: str = Field(default="LY Watchdog")
    app_version: str = Field(default="0.1.0")

    # Database — expects SQLAlchemy async URL (e.g. postgresql+asyncpg://...)
    database_url: str = Field(
        default="postgresql+asyncpg://watchdog:watchdog_dev@localhost:5432/ly_watchdog"
    )

    # DB pool
    db_pool_size: int = Field(default=5)
    db_max_overflow: int = Field(default=10)


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
