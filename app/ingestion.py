"""Ingestion pipeline: documents -> chunks -> embeddings -> vector store."""

import logging
from pathlib import Path

import psycopg

from app.chunking import Chunk, chunk_text
from app.config import Settings
from app.documents import Document, load_directory
from app.embeddings import Embedder
from app.vector_store import connect, count_sample_chunks, init_schema, replace_document

logger = logging.getLogger(__name__)

SAMPLE_DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_docs"


def ensure_sample_documents(settings: Settings, embedder: Embedder) -> None:
    """Create the schema and index the sample documents if the database has none yet."""
    with connect(settings) as conn:
        init_schema(conn, settings.embedding_dimensions)
        if count_sample_chunks(conn) > 0:
            logger.info("Sample documents already indexed")
            return
        total = ingest_documents(conn, embedder, load_directory(SAMPLE_DOCS_DIR), is_sample=True)
        logger.info("Indexed sample documents on startup (%d chunks)", total)


def ingest_documents(
    conn: psycopg.Connection,
    embedder: Embedder,
    documents: list[Document],
    is_sample: bool,
) -> int:
    """Index documents and return how many chunks were stored.

    All chunks are embedded in batched calls (not one call per document) to keep
    latency low and stay well within the embedding provider's rate limits.
    """
    chunks_by_source: dict[str, list[Chunk]] = {}
    for document in documents:
        chunks = chunk_text(document.source, document.text)
        if chunks:
            chunks_by_source[document.source] = chunks
        else:
            logger.warning("No text found in %s, skipping", document.source)

    all_chunks = [chunk for chunks in chunks_by_source.values() for chunk in chunks]
    if not all_chunks:
        return 0
    all_embeddings = embedder.embed_documents([chunk.content for chunk in all_chunks])

    position = 0
    for source, chunks in chunks_by_source.items():
        embeddings = all_embeddings[position : position + len(chunks)]
        position += len(chunks)
        replace_document(conn, source, chunks, embeddings, is_sample)
        logger.info("Indexed %s (%d chunks)", source, len(chunks))
    return len(all_chunks)
