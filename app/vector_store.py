"""Store and search document chunks in Postgres using the pgvector extension."""

from dataclasses import dataclass

import psycopg

from app.chunking import Chunk
from app.config import Settings


@dataclass(frozen=True)
class SearchResult:
    source: str
    content: str
    similarity: float  # cosine similarity, 1.0 = identical meaning


def connect(settings: Settings) -> psycopg.Connection:
    if settings.database_url is None:
        raise ValueError("DATABASE_URL is not set")
    conn = psycopg.connect(settings.database_url.get_secret_value(), connect_timeout=15)
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.commit()
    return conn


def init_schema(conn: psycopg.Connection, dimensions: int) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS chunks (
            id          BIGSERIAL PRIMARY KEY,
            source      TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content     TEXT NOT NULL,
            embedding   VECTOR({int(dimensions)}) NOT NULL,
            is_sample   BOOLEAN NOT NULL DEFAULT TRUE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (source, chunk_index)
        )
        """
    )
    # HNSW index: approximate nearest-neighbour search that stays fast as data grows.
    conn.execute(
        "CREATE INDEX IF NOT EXISTS chunks_embedding_idx "
        "ON chunks USING hnsw (embedding vector_cosine_ops)"
    )
    conn.commit()


def replace_document(
    conn: psycopg.Connection,
    source: str,
    chunks: list[Chunk],
    embeddings: list[list[float]],
    is_sample: bool,
) -> None:
    """Delete any previous version of the document and insert the new chunks atomically."""
    if len(chunks) != len(embeddings):
        raise ValueError("Each chunk needs exactly one embedding")
    with conn.transaction():
        # Scoped by is_sample so an upload can never overwrite a sample document.
        conn.execute("DELETE FROM chunks WHERE source = %s AND is_sample = %s", (source, is_sample))
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO chunks (source, chunk_index, content, embedding, is_sample) "
                "VALUES (%s, %s, %s, %s::vector, %s)",
                [
                    (chunk.source, chunk.index, chunk.content, str(vector), is_sample)
                    for chunk, vector in zip(chunks, embeddings, strict=True)
                ],
            )


def search(
    conn: psycopg.Connection, query_embedding: list[float], limit: int
) -> list[SearchResult]:
    # "<=>" is pgvector's cosine distance operator; similarity = 1 - distance.
    rows = conn.execute(
        "SELECT source, content, 1 - (embedding <=> %s::vector) AS similarity "
        "FROM chunks ORDER BY embedding <=> %s::vector LIMIT %s",
        (str(query_embedding), str(query_embedding), limit),
    ).fetchall()
    return [SearchResult(source=r[0], content=r[1], similarity=float(r[2])) for r in rows]


def delete_uploaded(conn: psycopg.Connection, older_than_hours: float | None = None) -> int:
    """Delete visitor-uploaded chunks (all, or only expired ones). Sample docs are kept."""
    if older_than_hours is None:
        cursor = conn.execute("DELETE FROM chunks WHERE is_sample = FALSE")
    else:
        cursor = conn.execute(
            "DELETE FROM chunks WHERE is_sample = FALSE "
            "AND created_at < now() - make_interval(secs => %s)",
            (older_than_hours * 3600,),
        )
    conn.commit()
    return cursor.rowcount


def count_chunks(conn: psycopg.Connection) -> int:
    row = conn.execute("SELECT count(*) FROM chunks").fetchone()
    return int(row[0]) if row else 0
