"""Index the sample clinic documents into the vector store.

Safe to run repeatedly: each document's previous chunks are replaced, never duplicated.

Usage:
    python scripts/ingest.py
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.documents import load_directory  # noqa: E402
from app.embeddings import Embedder  # noqa: E402
from app.ingestion import SAMPLE_DOCS_DIR, ingest_documents  # noqa: E402
from app.vector_store import connect, count_chunks, init_schema  # noqa: E402


def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(levelname)s %(message)s")

    documents = load_directory(SAMPLE_DOCS_DIR)
    embedder = Embedder(settings)

    with connect(settings) as conn:
        init_schema(conn, settings.embedding_dimensions)
        total = ingest_documents(conn, embedder, documents, is_sample=True)
        print(f"\nIndexed {len(documents)} documents into {total} chunks.")
        print(f"Chunks in database: {count_chunks(conn)}")


if __name__ == "__main__":
    main()
