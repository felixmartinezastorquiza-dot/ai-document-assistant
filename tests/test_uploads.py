from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.documents import Document
from app.main import app, get_indexer, render_author_footer
from app.uploads import UploadRejectedError, safe_source_name, validate_upload

SETTINGS = Settings(max_upload_bytes=1_000, max_upload_chars=500)


def test_upload_names_are_prefixed_and_sanitized() -> None:
    assert safe_source_name("pricing.pdf") == "uploaded-pricing.pdf"
    assert safe_source_name("../../etc/passwd.txt") == "uploaded-passwd.txt"
    assert safe_source_name("<script>.md") == "uploaded-_script_.md"


def test_valid_upload_becomes_a_document() -> None:
    document = validate_upload("menu.txt", b"Pizza costs $10.", SETTINGS)

    assert document == Document(source="uploaded-menu.txt", text="Pizza costs $10.")


@pytest.mark.parametrize(
    ("filename", "data", "reason"),
    [
        ("photo.png", b"\x89PNG", "Only PDF"),
        ("big.txt", b"x" * 2_000, "too large"),
        ("long.txt", b"word " * 150, "too long"),
        ("empty.txt", b"   ", "No text found"),
        ("broken.pdf", b"not really a pdf", "could not be read"),
    ],
)
def test_invalid_uploads_are_rejected_with_a_clear_reason(
    filename: str, data: bytes, reason: str
) -> None:
    with pytest.raises(UploadRejectedError, match=reason):
        validate_upload(filename, data, SETTINGS)


def test_author_footer_escapes_values_and_skips_empty_links() -> None:
    config = Settings(
        author_name="Ana <b>",
        author_title="Dev",
        author_github_url="https://github.com/ana",
        author_upwork_url="",
        author_linkedin_url="",
    )

    footer = render_author_footer(config)

    assert "Ana &lt;b&gt;" in footer
    assert 'href="https://github.com/ana"' in footer
    assert "Upwork" not in footer
    assert "LinkedIn" not in footer


class StubIndexer:
    def __init__(self) -> None:
        self.added: list[Document] = []

    def add(self, document: Document) -> int:
        self.added.append(document)
        return 3

    def reset(self) -> int:
        return 7


@pytest.fixture
def indexer() -> Iterator[StubIndexer]:
    stub = StubIndexer()
    app.dependency_overrides[get_indexer] = lambda: stub
    yield stub
    app.dependency_overrides.clear()


def test_upload_endpoint_indexes_the_file(indexer: StubIndexer) -> None:
    client = TestClient(app)

    response = client.post(
        "/documents", files={"file": ("menu.txt", b"Pizza costs $10.", "text/plain")}
    )

    assert response.status_code == 200
    assert response.json() == {"source": "uploaded-menu.txt", "chunks": 3}
    assert indexer.added[0].text == "Pizza costs $10."


def test_upload_endpoint_rejects_unsupported_files(indexer: StubIndexer) -> None:
    client = TestClient(app)

    response = client.post("/documents", files={"file": ("photo.png", b"\x89PNG", "image/png")})

    assert response.status_code == 400
    assert "Only PDF" in response.json()["detail"]
    assert indexer.added == []


def test_reset_endpoint_reports_deleted_chunks(indexer: StubIndexer) -> None:
    response = TestClient(app).post("/reset")

    assert response.status_code == 200
    assert response.json() == {"deleted_chunks": 7}
