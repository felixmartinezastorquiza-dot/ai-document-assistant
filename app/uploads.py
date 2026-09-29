"""Visitor document uploads: validation, indexing and demo reset."""

import logging
import re
from pathlib import Path
from typing import Protocol

import psycopg
import voyageai.error

from app.config import Settings
from app.documents import Document, UnsupportedFileTypeError, extract_text
from app.embeddings import Embedder
from app.ingestion import ingest_documents
from app.vector_store import connect, delete_uploaded, init_schema

logger = logging.getLogger(__name__)

UPLOAD_PREFIX = "uploaded-"


class UploadRejectedError(ValueError):
    """The file can't be accepted (type, size, no readable text...)."""


class IndexingUnavailableError(RuntimeError):
    """The file is valid but the embedding service or database is unreachable."""


def safe_source_name(filename: str) -> str:
    """Keep only a short, harmless file name, prefixed so it never clashes with sample docs."""
    name = Path(filename).name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip() or "document"
    return UPLOAD_PREFIX + name[-80:]


def validate_upload(filename: str, data: bytes, settings: Settings) -> Document:
    if len(data) > settings.max_upload_bytes:
        limit_mb = settings.max_upload_bytes / 1_000_000
        raise UploadRejectedError(f"The file is too large. Maximum size is {limit_mb:g} MB.")
    try:
        text = extract_text(filename, data)
    except UnsupportedFileTypeError as exc:
        raise UploadRejectedError(
            "Only PDF, Markdown (.md) and text (.txt) files are supported."
        ) from exc
    except Exception as exc:  # corrupted or encrypted PDFs raise various pypdf errors
        logger.warning("Could not read upload %r: %s", filename, exc)
        raise UploadRejectedError("The file could not be read. Is it a valid document?") from exc

    if not text.strip():
        raise UploadRejectedError(
            "No text found in this file. Scanned PDFs (images) are not supported."
        )
    if len(text) > settings.max_upload_chars:
        limit = f"{settings.max_upload_chars:,}"
        raise UploadRejectedError(
            f"The document is too long for this demo (max {limit} characters)."
        )
    return Document(source=safe_source_name(filename), text=text)


class DocumentIndexer(Protocol):
    def add(self, document: Document) -> int: ...

    def reset(self) -> int: ...


class PgDocumentIndexer:
    def __init__(self, settings: Settings, embedder: Embedder) -> None:
        self._settings = settings
        self._embedder = embedder

    def add(self, document: Document) -> int:
        try:
            with connect(self._settings) as conn:
                init_schema(conn, self._settings.embedding_dimensions)
                expired = delete_uploaded(conn, older_than_hours=self._settings.upload_ttl_hours)
                if expired:
                    logger.info("Removed %d expired uploaded chunks", expired)
                return ingest_documents(conn, self._embedder, [document], is_sample=False)
        except voyageai.error.RateLimitError as exc:
            raise IndexingUnavailableError(
                "The demo is receiving many requests. Please try again in a minute."
            ) from exc
        except (voyageai.error.VoyageError, psycopg.Error) as exc:
            logger.error("Indexing failed: %s", exc)
            raise IndexingUnavailableError(
                "The document could not be indexed right now. Please try again later."
            ) from exc

    def reset(self) -> int:
        try:
            with connect(self._settings) as conn:
                return delete_uploaded(conn)
        except psycopg.Error as exc:
            logger.error("Reset failed: %s", exc)
            raise IndexingUnavailableError("The demo could not be reset right now.") from exc
