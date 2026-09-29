"""Application settings loaded from environment variables (and a local .env file)."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Document Assistant"
    log_level: str = "INFO"

    # Chat model (answers questions). Switch provider without code changes.
    llm_provider: Literal["anthropic", "openai"] = "anthropic"
    chat_model: str = "claude-haiku-4-5"
    anthropic_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None

    # Embedding model (turns text into vectors for semantic search).
    embedding_model: str = "voyage-3.5-lite"
    voyage_api_key: SecretStr | None = None

    database_url: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
