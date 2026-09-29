"""FastAPI entry point."""

import html
import logging
import math
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.embeddings import Embedder
from app.ingestion import ensure_sample_documents
from app.llm import ChatModel, LLMUnavailableError, create_chat_model
from app.rag import Retriever, answer_question
from app.rate_limit import DailyQuota, SlidingWindowRateLimiter, client_ip
from app.retrieval import PgVectorRetriever, RetrievalUnavailableError
from app.uploads import (
    DocumentIndexer,
    IndexingUnavailableError,
    PgDocumentIndexer,
    UploadRejectedError,
    validate_upload,
)

settings = get_settings()

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.auto_ingest_samples:
        try:
            await run_in_threadpool(ensure_sample_documents, settings, get_embedder())
        except Exception:  # the app should still start and report errors per request
            logger.exception("Could not index sample documents on startup")
    yield


app = FastAPI(
    title=settings.app_name,
    description="RAG assistant that answers questions from a clinic's documents, with sources.",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

chat_limiter = SlidingWindowRateLimiter(settings.rate_limit_chat_per_minute, window_seconds=60)
upload_limiter = SlidingWindowRateLimiter(settings.rate_limit_uploads_per_hour, window_seconds=3600)
chat_quota = DailyQuota(settings.max_daily_chat_requests)
upload_quota = DailyQuota(settings.max_daily_uploads)


def enforce_limits(
    request: Request, limiter: SlidingWindowRateLimiter, quota: DailyQuota, action: str
) -> None:
    retry_after = limiter.check(client_ip(request, settings.trusted_proxy_hops))
    if retry_after is not None:
        seconds = math.ceil(retry_after)
        raise HTTPException(
            status_code=429,
            detail=f"Too many {action} in a short time. Please wait {seconds} seconds.",
            headers={"Retry-After": str(seconds)},
        )
    if not quota.consume():
        raise HTTPException(
            status_code=429,
            detail="This demo has reached its daily usage limit. Please come back tomorrow.",
        )


def limit_chat(request: Request) -> None:
    enforce_limits(request, chat_limiter, chat_quota, "questions")


def limit_uploads(request: Request) -> None:
    enforce_limits(request, upload_limiter, upload_quota, "uploads")


def reset_rate_limits() -> None:
    for guard in (chat_limiter, upload_limiter, chat_quota, upload_quota):
        guard.reset()


class ChatRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=settings.max_question_chars,
        examples=["Can I drink coffee after teeth whitening?"],
    )


class CitationOut(BaseModel):
    source: str
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    answered: bool
    citations: list[CitationOut]


class UploadResponse(BaseModel):
    source: str
    chunks: int


class ResetResponse(BaseModel):
    deleted_chunks: int


@lru_cache
def get_embedder() -> Embedder:
    return Embedder(settings)


@lru_cache
def get_retriever() -> Retriever:
    return PgVectorRetriever(settings, get_embedder())


@lru_cache
def get_chat_model() -> ChatModel:
    return create_chat_model(settings)


@lru_cache
def get_indexer() -> DocumentIndexer:
    return PgDocumentIndexer(settings, get_embedder())


def render_author_footer(config: Settings) -> str:
    """Author signature for the footer. All values are escaped; empty links are skipped."""
    links = {
        "Upwork": config.author_upwork_url,
        "GitHub": config.author_github_url,
        "LinkedIn": config.author_linkedin_url,
    }
    parts = [
        f"Built by <strong>{html.escape(config.author_name)}</strong>",
        html.escape(config.author_title),
    ]
    parts += [
        f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{label}</a>'
        for label, url in links.items()
        if url
    ]
    return " · ".join(parts)


@lru_cache
def render_chat_page() -> str:
    page = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return page.replace("<!-- AUTHOR_SIGNATURE -->", render_author_footer(settings))


@app.get("/", include_in_schema=False)
def chat_page() -> HTMLResponse:
    """The web chat UI."""
    return HTMLResponse(render_chat_page())


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check used by Docker and the hosting platform."""
    return {"status": "ok"}


@app.post("/chat", dependencies=[Depends(limit_chat)])
def chat(
    request: ChatRequest,
    retriever: Annotated[Retriever, Depends(get_retriever)],
    chat_model: Annotated[ChatModel, Depends(get_chat_model)],
) -> ChatResponse:
    """Answer a patient question from the clinic's documents, with cited sources."""
    try:
        result = answer_question(
            request.question.strip(), retriever, chat_model, settings.retrieval_top_k
        )
    except (RetrievalUnavailableError, LLMUnavailableError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ChatResponse(
        answer=result.answer,
        answered=result.answered,
        citations=[CitationOut(source=c.source, excerpt=c.excerpt) for c in result.citations],
    )


@app.post("/documents", dependencies=[Depends(limit_uploads)])
async def upload_document(
    file: UploadFile,
    indexer: Annotated[DocumentIndexer, Depends(get_indexer)],
) -> UploadResponse:
    """Upload a PDF, Markdown or TXT file so the assistant can answer questions about it."""
    data = await file.read(settings.max_upload_bytes + 1)  # never read more than needed
    try:
        document = validate_upload(file.filename or "document.txt", data, settings)
        # Indexing blocks on network calls: run it off the event loop.
        chunks = await run_in_threadpool(indexer.add, document)
    except UploadRejectedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IndexingUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    logger.info("Visitor uploaded %s (%d chunks)", document.source, chunks)
    return UploadResponse(source=document.source, chunks=chunks)


@app.post("/reset")
def reset_demo(indexer: Annotated[DocumentIndexer, Depends(get_indexer)]) -> ResetResponse:
    """Remove every visitor-uploaded document. The clinic's sample documents are kept."""
    try:
        deleted = indexer.reset()
    except IndexingUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    logger.info("Demo reset: %d uploaded chunks deleted", deleted)
    return ResetResponse(deleted_chunks=deleted)
