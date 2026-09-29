from pathlib import Path

import pytest

from app.documents import UnsupportedFileTypeError, extract_text, load_directory

SAMPLE_DOCS = Path(__file__).resolve().parent.parent / "data" / "sample_docs"


def test_reads_plain_text_and_markdown() -> None:
    assert extract_text("notes.txt", b"Hello clinic") == "Hello clinic"
    assert extract_text("notes.md", b"# Title\n") == "# Title"


def test_rejects_unsupported_file_types() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        extract_text("photo.png", b"\x89PNG")


def test_loads_all_sample_documents_including_pdf() -> None:
    documents = {doc.source: doc.text for doc in load_directory(SAMPLE_DOCS)}

    assert set(documents) == {
        "faq.md",
        "opening-hours.md",
        "policies.txt",
        "pricing.pdf",
        "treatment-preparation.md",
    }
    assert "$95" in documents["pricing.pdf"]
