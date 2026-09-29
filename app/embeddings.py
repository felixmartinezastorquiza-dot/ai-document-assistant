"""Text embeddings via Voyage AI."""

from typing import Literal

import voyageai

from app.config import Settings

BATCH_SIZE = 128

InputType = Literal["document", "query"]


class Embedder:
    def __init__(self, settings: Settings) -> None:
        if settings.voyage_api_key is None:
            raise ValueError("VOYAGE_API_KEY is not set")
        self._client = voyageai.Client(api_key=settings.voyage_api_key.get_secret_value())
        self._model = settings.embedding_model

    def _embed(self, texts: list[str], input_type: InputType) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start : start + BATCH_SIZE]
            result = self._client.embed(batch, model=self._model, input_type=input_type)
            vectors.extend(result.embeddings)
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, "document")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "query")[0]

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, "query")
