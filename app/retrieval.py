"""Semantic search over the indexed chunks: embed the question, then query pgvector."""

import logging

import psycopg
import voyageai.error

from app.config import Settings
from app.embeddings import Embedder
from app.vector_store import SearchResult, connect, search

logger = logging.getLogger(__name__)


class RetrievalUnavailableError(RuntimeError):
    """Search failed because the embedding service or the database is unreachable."""


class PgVectorRetriever:
    def __init__(self, settings: Settings, embedder: Embedder) -> None:
        self._settings = settings
        self._embedder = embedder

    def retrieve(self, question: str, limit: int) -> list[SearchResult]:
        try:
            query_embedding = self._embedder.embed_query(question)
        except voyageai.error.RateLimitError as exc:
            logger.warning("Embedding rate limit reached: %s", exc)
            raise RetrievalUnavailableError(
                "The demo is receiving many requests. Please try again in a minute."
            ) from exc
        except voyageai.error.VoyageError as exc:
            logger.error("Embedding service error: %s", exc)
            raise RetrievalUnavailableError(
                "The search service is temporarily unavailable."
            ) from exc

        try:
            with connect(self._settings) as conn:
                return search(conn, query_embedding, limit)
        except psycopg.Error as exc:
            logger.error("Database error: %s", exc)
            raise RetrievalUnavailableError(
                "The document database is temporarily unavailable."
            ) from exc
