"""Chat model providers behind one small interface, selected with LLM_PROVIDER."""

import logging
from typing import Protocol

import anthropic
from pydantic import BaseModel, Field

from app.config import Settings

logger = logging.getLogger(__name__)


class LLMUnavailableError(RuntimeError):
    """The chat model could not produce an answer (network, quota, outage...)."""


class GroundedAnswer(BaseModel):
    """Structured output the model must return for every question."""

    answer_found: bool = Field(
        description="True only if the context snippets contain the answer to the question."
    )
    answer: str = Field(description="The answer, or an empty string if answer_found is false.")
    source_ids: list[int] = Field(
        description="Numbers of the context snippets the answer is based on."
    )


class ChatModel(Protocol):
    def generate(self, system: str, user: str) -> GroundedAnswer: ...


class AnthropicChatModel:
    def __init__(self, settings: Settings) -> None:
        if settings.anthropic_api_key is None:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())
        self._model = settings.chat_model
        self._max_tokens = settings.max_answer_tokens

    def generate(self, system: str, user: str) -> GroundedAnswer:
        try:
            response = self._client.messages.parse(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=GroundedAnswer,
            )
        except anthropic.APIError as exc:
            logger.error("Anthropic API error: %s", exc)
            raise LLMUnavailableError("The AI service is temporarily unavailable.") from exc

        if response.parsed_output is None:
            # e.g. a refusal or a truncated response: treat it as "no answer", never crash.
            logger.warning("No structured output (stop_reason=%s)", response.stop_reason)
            return GroundedAnswer(answer_found=False, answer="", source_ids=[])
        return response.parsed_output


class OpenAIChatModel:
    """Optional provider. Requires `pip install openai` and LLM_PROVIDER=openai."""

    def __init__(self, settings: Settings) -> None:
        import openai  # imported lazily so the default install doesn't need it

        if settings.openai_api_key is None:
            raise ValueError("OPENAI_API_KEY is not set")
        self._openai = openai
        self._client = openai.OpenAI(api_key=settings.openai_api_key.get_secret_value())
        self._model = settings.chat_model
        self._max_tokens = settings.max_answer_tokens

    def generate(self, system: str, user: str) -> GroundedAnswer:
        try:
            completion = self._client.chat.completions.parse(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format=GroundedAnswer,
            )
        except self._openai.OpenAIError as exc:
            logger.error("OpenAI API error: %s", exc)
            raise LLMUnavailableError("The AI service is temporarily unavailable.") from exc

        parsed = completion.choices[0].message.parsed
        return parsed or GroundedAnswer(answer_found=False, answer="", source_ids=[])


def create_chat_model(settings: Settings) -> ChatModel:
    if settings.llm_provider == "openai":
        return OpenAIChatModel(settings)
    return AnthropicChatModel(settings)
