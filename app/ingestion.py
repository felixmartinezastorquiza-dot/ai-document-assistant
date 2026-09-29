"""Ingestion pipeline: documents -> chunks -> embeddings -> vector store."""

import logging

import psycopg

from app.chunking import Chunk, chunk_text
from app.documents import Document
from app.embeddings import Embedder
from app.vector_store import replace_document

logger = logging.getLogger(__name__)


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
