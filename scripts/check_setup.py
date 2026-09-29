"""Verify that every external service is reachable with the configured credentials.

Makes one tiny call per service (costs a fraction of a cent) and never prints secrets.

Usage:
    python scripts/check_setup.py
"""

import sys
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import anthropic  # noqa: E402
import psycopg  # noqa: E402
import voyageai  # noqa: E402

from app.config import Settings, get_settings  # noqa: E402


def check_database(settings: Settings) -> str:
    if settings.database_url is None:
        raise ValueError("DATABASE_URL is not set")
    with psycopg.connect(settings.database_url.get_secret_value(), connect_timeout=15) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        query = "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        row = conn.execute(query).fetchone()
    return f"connected, pgvector {row[0] if row else 'missing'}"


def check_embeddings(settings: Settings) -> str:
    if settings.voyage_api_key is None:
        raise ValueError("VOYAGE_API_KEY is not set")
    client = voyageai.Client(api_key=settings.voyage_api_key.get_secret_value())
    result = client.embed(["test"], model=settings.embedding_model, input_type="query")
    return f"{settings.embedding_model}, {len(result.embeddings[0])} dimensions"


def check_chat(settings: Settings) -> str:
    if settings.anthropic_api_key is None:
        raise ValueError("ANTHROPIC_API_KEY is not set")
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())
    message = client.messages.create(
        model=settings.chat_model,
        max_tokens=10,
        messages=[{"role": "user", "content": "Reply with: OK"}],
    )
    return f"{message.model} replied"


CHECKS: dict[str, Callable[[Settings], str]] = {
    "Database (Postgres + pgvector)": check_database,
    "Embeddings (Voyage AI)": check_embeddings,
    "Chat (Anthropic)": check_chat,
}


def main() -> int:
    settings = get_settings()
    failures = 0
    for name, check in CHECKS.items():
        try:
            print(f"[OK]   {name}: {check(settings)}")
        except Exception as exc:  # report every failure instead of stopping at the first
            failures += 1
            print(f"[FAIL] {name}: {type(exc).__name__}: {str(exc)[:200]}")
    print("\nAll services ready." if failures == 0 else f"\n{failures} check(s) failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
