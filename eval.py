"""Evaluate the assistant end to end on the question set in eval/questions.json.

In-scope questions pass when the answer contains every expected keyword AND cites the
expected document. Out-of-scope questions pass when the assistant declines to answer.

Uses the real pipeline (pgvector search + chat model + citation rules). All questions are
embedded in a single call to stay within embedding rate limits.

Usage:
    python eval.py
"""

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.embeddings import Embedder
from app.llm import create_chat_model
from app.rag import RagAnswer, answer_question
from app.vector_store import SearchResult, connect, search

QUESTIONS_PATH = Path(__file__).resolve().parent / "eval" / "questions.json"
MIN_IN_SCOPE_CORRECT = 9


@dataclass(frozen=True)
class CaseResult:
    id: int
    question: str
    passed: bool
    detail: str


class PrecomputedRetriever:
    """Searches pgvector with query embeddings computed up front in one batch."""

    def __init__(self, conn, embeddings_by_question: dict[str, list[float]]) -> None:
        self._conn = conn
        self._embeddings = embeddings_by_question

    def retrieve(self, question: str, limit: int) -> list[SearchResult]:
        return search(self._conn, self._embeddings[question], limit)


def grade_in_scope(case: dict, result: RagAnswer) -> CaseResult:
    sources = [c.source for c in result.citations]
    missing = [kw for kw in case["must_include"] if kw.lower() not in result.answer.lower()]
    problems = []
    if not result.answered:
        problems.append("declined to answer")
    if missing:
        problems.append(f"missing {missing}")
    if case["expected_source"] not in sources:
        problems.append(f"cited {sources or 'nothing'}, expected {case['expected_source']}")
    detail = "; ".join(problems) if problems else f"cited {case['expected_source']}"
    return CaseResult(case["id"], case["question"], not problems, detail)


def grade_out_of_scope(case: dict, result: RagAnswer) -> CaseResult:
    passed = not result.answered
    detail = "declined correctly" if passed else f"answered: {result.answer[:60]!r}"
    return CaseResult(case["id"], case["question"], passed, detail)


def print_section(title: str, results: list[CaseResult]) -> None:
    print(f"\n{title}")
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        print(f"  [{mark}] #{r.id:>2} {r.question:<55} {r.detail}")


def main() -> int:
    settings = get_settings()
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    in_scope, out_of_scope = data["in_scope"], data["out_of_scope"]
    questions = [case["question"] for case in in_scope + out_of_scope]

    print(f"Evaluating {len(questions)} questions with {settings.chat_model}...")
    started = time.perf_counter()
    embeddings = dict(zip(questions, Embedder(settings).embed_queries(questions), strict=True))
    chat_model = create_chat_model(settings)

    with connect(settings) as conn:
        retriever = PrecomputedRetriever(conn, embeddings)

        def ask(case: dict) -> RagAnswer:
            return answer_question(
                case["question"], retriever, chat_model, settings.retrieval_top_k
            )

        in_results = [grade_in_scope(case, ask(case)) for case in in_scope]
        out_results = [grade_out_of_scope(case, ask(case)) for case in out_of_scope]

    print_section(
        "In-scope questions (answer must be correct and cite the right document)", in_results
    )
    print_section("Out-of-scope questions (assistant must decline)", out_results)

    in_passed = sum(r.passed for r in in_results)
    out_passed = sum(r.passed for r in out_results)
    ok = in_passed >= MIN_IN_SCOPE_CORRECT and out_passed == len(out_results)

    in_total, out_total = len(in_results), len(out_results)
    print("\nSummary")
    print(
        f"  In-scope correct with source: {in_passed}/{in_total} (target >= {MIN_IN_SCOPE_CORRECT})"
    )
    print(f"  Out-of-scope declined:        {out_passed}/{out_total} (target {out_total})")
    print(f"  Time: {time.perf_counter() - started:.1f}s")
    print(f"  Result: {'PASSED' if ok else 'FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
