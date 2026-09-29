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
    embedding_dimensions: int = 1024
    voyage_api_key: SecretStr | None = None

    database_url: SecretStr | None = None

    # RAG behaviour and cost guards
    retrieval_top_k: int = 4  # how many chunks the model gets as context
    max_answer_tokens: int = 400  # hard cap on tokens generated per answer
    max_question_chars: int = 500

    # Visitor uploads
    max_upload_bytes: int = 2_000_000  # 2 MB
    max_upload_chars: int = 60_000  # caps embedding cost per upload
    upload_ttl_hours: float = 24  # uploads are deleted automatically after this

    # Author signature shown in the page footer (empty links are hidden)
    author_name: str = "Felix Martinez"
    author_title: str = "Python & AI Integration Developer"
    author_upwork_url: str = ""
    author_github_url: str = ""
    author_linkedin_url: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
