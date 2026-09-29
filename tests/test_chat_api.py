from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.llm import GroundedAnswer, LLMUnavailableError
from app.main import app, get_chat_model, get_retriever
from app.vector_store import SearchResult


class StubRetriever:
    def retrieve(self, question: str, limit: int) -> list[SearchResult]:
        return [SearchResult(source="faq.md", content="Free parking.", similarity=0.7)]


class StubChatModel:
    def generate(self, system: str, user: str) -> GroundedAnswer:
        return GroundedAnswer(answer_found=True, answer="Yes, parking is free.", source_ids=[1])


class FailingChatModel:
    def generate(self, system: str, user: str) -> GroundedAnswer:
        raise LLMUnavailableError("The AI service is temporarily unavailable.")


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_retriever] = StubRetriever
    app.dependency_overrides[get_chat_model] = StubChatModel
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_chat_returns_answer_with_citations(client: TestClient) -> None:
    response = client.post("/chat", json={"question": "Is there parking?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answered"] is True
    assert body["answer"] == "Yes, parking is free."
    assert body["citations"] == [{"source": "faq.md", "excerpt": "Free parking."}]


def test_chat_rejects_empty_and_too_long_questions(client: TestClient) -> None:
    assert client.post("/chat", json={"question": ""}).status_code == 422
    assert client.post("/chat", json={"question": "x" * 5000}).status_code == 422


def test_chat_reports_ai_outage_clearly(client: TestClient) -> None:
    app.dependency_overrides[get_chat_model] = FailingChatModel

    response = client.post("/chat", json={"question": "Is there parking?"})

    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]
