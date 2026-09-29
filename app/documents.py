"""Turn supported files (PDF, Markdown, plain text) into plain text."""

import io
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt"}


class UnsupportedFileTypeError(ValueError):
    pass


@dataclass(frozen=True)
class Document:
    source: str  # file name shown to users when citing
    text: str


def extract_text(filename: str, data: bytes) -> str:
    """Extract text from raw file bytes. Works for files on disk and for uploads."""
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{extension}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )
    if extension == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()
    return data.decode("utf-8", errors="replace").strip()


def load_document(path: Path) -> Document:
    return Document(source=path.name, text=extract_text(path.name, path.read_bytes()))


def load_directory(directory: Path) -> list[Document]:
    paths = sorted(p for p in directory.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)
    return [load_document(p) for p in paths]
