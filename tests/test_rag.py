from app.llm import GroundedAnswer
from app.rag import FALLBACK_ANSWER, answer_question, build_user_message
from app.vector_store import SearchResult

RESULTS = [
    SearchResult(source="pricing.pdf", content="Routine cleaning (adults) $95", similarity=0.6),
    SearchResult(source="faq.md", content="Free parking behind the building.", similarity=0.4),
]


class FakeRetriever:
    def __init__(self, results: list[SearchResult]) -> None:
        self.results = results

    def retrieve(self, question: str, limit: int) -> list[SearchResult]:
        return self.results[:limit]


class FakeChatModel:
    def __init__(self, output: GroundedAnswer) -> None:
        self.output = output
        self.last_user_message = ""

    def generate(self, system: str, user: str) -> GroundedAnswer:
        self.last_user_message = user
        return self.output


def ask(output: GroundedAnswer, results: list[SearchResult] = RESULTS):
    return answer_question(
        "How much is a cleaning?", FakeRetriever(results), FakeChatModel(output), 4
    )


def test_grounded_answer_includes_citation_from_search_results() -> None:
    result = ask(GroundedAnswer(answer_found=True, answer="It costs $95.", source_ids=[1]))

    assert result.answered
    assert result.answer == "It costs $95."
    assert [c.source for c in result.citations] == ["pricing.pdf"]
    assert result.citations[0].excerpt == "Routine cleaning (adults) $95"


def test_not_found_returns_fixed_fallback_message() -> None:
    result = ask(GroundedAnswer(answer_found=False, answer="", source_ids=[]))

    assert not result.answered
    assert result.answer == FALLBACK_ANSWER
    assert result.citations == []


def test_answer_without_valid_sources_is_rejected() -> None:
    # The model claims an answer but cites a snippet that doesn't exist: don't trust it.
    result = ask(GroundedAnswer(answer_found=True, answer="Braces cost $5,000.", source_ids=[9]))

    assert not result.answered
    assert result.answer == FALLBACK_ANSWER


def test_duplicate_source_ids_produce_one_citation() -> None:
    result = ask(GroundedAnswer(answer_found=True, answer="$95.", source_ids=[1, 1]))

    assert len(result.citations) == 1


def test_no_search_results_skips_the_model() -> None:
    model = FakeChatModel(GroundedAnswer(answer_found=True, answer="x", source_ids=[1]))

    result = answer_question("Anything?", FakeRetriever([]), model, 4)

    assert result.answer == FALLBACK_ANSWER
    assert model.last_user_message == ""  # model was never called


def test_user_message_numbers_snippets_and_names_sources() -> None:
    message = build_user_message("How much?", RESULTS)

    assert "[1] (source: pricing.pdf)" in message
    assert "[2] (source: faq.md)" in message
    assert message.endswith("Question: How much?")
