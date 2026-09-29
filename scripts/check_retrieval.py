"""Check that semantic search finds the expected source document for each eval question.

Tests retrieval only (no chat model involved). Uses a single embedding call for all questions.

Usage:
    python scripts/check_retrieval.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.embeddings import Embedder  # noqa: E402
from app.vector_store import connect, search  # noqa: E402

QUESTIONS_PATH = ROOT / "eval" / "questions.json"
TOP_K = 3


def main() -> int:
    settings = get_settings()
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    questions = data["in_scope"] + data["out_of_scope"]
    vectors = Embedder(settings).embed_queries([q["question"] for q in questions])

    hits = 0
    with connect(settings) as conn:
        for question, vector in zip(questions, vectors, strict=True):
            results = search(conn, vector, limit=TOP_K)
            expected = question.get("expected_source")
            found = expected in {r.source for r in results} if expected else None
            hits += bool(found)
            label = "OK  " if found else ("MISS" if expected else "n/a ")
            best = results[0]
            print(
                f"{label} #{question['id']:>2}  best={best.source:<26} "
                f"similarity={best.similarity:.2f}  {question['question'][:55]}"
            )

    in_scope = len(data["in_scope"])
    print(f"\nExpected source in top {TOP_K}: {hits}/{in_scope}")
    return 0 if hits == in_scope else 1


if __name__ == "__main__":
    sys.exit(main())
