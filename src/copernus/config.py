"""Configuration from environment / .env. Units in names, no literals in code."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="COP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://copernus:copernus@localhost:5433/copernus"
    migration_database_url: str = Field(
        default="postgresql+asyncpg://copernus:copernus@localhost:5433/copernus",
        repr=False,
    )

    auth_email_domain: str = "example.com"
    session_ttl_hours: int = 12
    session_cookie_secure: bool = False  # true behind HTTPS


def load_settings() -> Settings:
    return Settings()
