"""FastAPI entry point."""

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.embeddings import Embedder
from app.llm import ChatModel, LLMUnavailableError, create_chat_model
from app.rag import Retriever, answer_question
from app.retrieval import PgVectorRetriever, RetrievalUnavailableError

settings = get_settings()

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=settings.max_question_chars)


class CitationOut(BaseModel):
    source: str
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    answered: bool
    citations: list[CitationOut]


@lru_cache
def get_retriever() -> Retriever:
    return PgVectorRetriever(settings, Embedder(settings))


@lru_cache
def get_chat_model() -> ChatModel:
    return create_chat_model(settings)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check used by Docker and the hosting platform."""
    return {"status": "ok"}


@app.post("/chat")
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
