"""Application settings loaded from environment variables (and a local .env file)."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Document Assistant"
    log_level: str = "INFO"

    openai_api_key: SecretStr | None = None
    chat_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    database_url: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
