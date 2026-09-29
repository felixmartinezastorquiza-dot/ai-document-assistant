"""Split documents into small, self-contained chunks for retrieval.

Strategy: split on section headings first, so an answer and its heading stay together
(e.g. "Saturday" and "9:00 AM"). Sections that are still too long are packed line by line,
repeating the heading and one line of overlap so no chunk loses its context.
"""

import re
from dataclasses import dataclass

# Markdown headings ("## Teeth whitening") or numbered uppercase headings ("1. PAYMENT").
HEADING_PATTERN = re.compile(r"^(#{1,6}\s+\S.*|\d+\.\s+[A-Z][A-Z0-9 /&'-]+)$")

DEFAULT_MAX_CHARS = 1000
DEFAULT_MIN_CHARS = 200


@dataclass(frozen=True)
class Chunk:
    source: str
    index: int
    content: str


def is_heading(line: str) -> bool:
    return bool(HEADING_PATTERN.match(line.strip()))


def split_into_sections(text: str) -> list[str]:
    sections: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if is_heading(line) and current:
            sections.append("\n".join(current).strip())
            current = []
        current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    return [section for section in sections if section]


def merge_small_sections(sections: list[str], min_chars: int) -> list[str]:
    """Attach tiny sections (like a document title) to the section that follows."""
    merged: list[str] = []
    pending = ""
    for section in sections:
        combined = f"{pending}\n\n{section}".strip() if pending else section
        if len(combined) < min_chars:
            pending = combined
        else:
            merged.append(combined)
            pending = ""
    if pending:
        if merged:
            merged[-1] = f"{merged[-1]}\n\n{pending}"
        else:
            merged.append(pending)
    return merged


def split_long_section(section: str, max_chars: int) -> list[str]:
    if len(section) <= max_chars:
        return [section]

    lines = [line for line in section.splitlines() if line.strip()]
    heading = lines[0] if is_heading(lines[0]) else None
    pieces: list[str] = []
    current: list[str] = []

    for line in lines:
        if current and len("\n".join([*current, line])) > max_chars:
            pieces.append("\n".join(current))
            overlap = current[-1]
            current = [heading, overlap] if heading and overlap != heading else [overlap]
        current.append(line)
    if current:
        pieces.append("\n".join(current))
    return pieces


def chunk_text(
    source: str,
    text: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    min_chars: int = DEFAULT_MIN_CHARS,
) -> list[Chunk]:
    sections = merge_small_sections(split_into_sections(text), min_chars)
    pieces = [piece for section in sections for piece in split_long_section(section, max_chars)]
    return [Chunk(source=source, index=i, content=piece) for i, piece in enumerate(pieces)]
