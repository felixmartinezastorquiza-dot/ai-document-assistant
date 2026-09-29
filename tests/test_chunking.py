from app.chunking import chunk_text, is_heading, split_into_sections

MARKDOWN = """# Clinic Hours

Intro line about the clinic that is long enough to stand on its own as a section here.

## Saturday
We are open from 9:00 AM to 1:00 PM on Saturdays, every week of the year.
Please book in advance because Saturday slots fill up quickly with families.

## Sunday
Closed. For emergencies call the after-hours line listed on our contact page.
"""


def test_detects_markdown_and_numbered_headings() -> None:
    assert is_heading("## Teeth whitening")
    assert is_heading("1. APPOINTMENT CANCELLATIONS")
    assert not is_heading("Payment is due at the time of service.")


def test_splits_on_headings() -> None:
    sections = split_into_sections(MARKDOWN)

    assert len(sections) == 3
    assert sections[1].startswith("## Saturday")


def test_heading_and_answer_stay_in_same_chunk() -> None:
    chunks = chunk_text("hours.md", MARKDOWN, min_chars=50)

    saturday = next(c for c in chunks if "Saturday" in c.content)
    assert "9:00 AM" in saturday.content


def test_tiny_sections_are_merged_into_the_next_one() -> None:
    text = "# Title\n\n## Section\n" + "Real content. " * 30

    chunks = chunk_text("doc.md", text)

    assert len(chunks) == 1
    assert chunks[0].content.startswith("# Title")


def test_long_sections_are_split_and_keep_their_heading() -> None:
    lines = [f"Line {i} with some filler text to make it longer." for i in range(40)]
    text = "## Long section\n" + "\n".join(lines)

    chunks = chunk_text("long.md", text, max_chars=300)

    assert len(chunks) > 1
    assert all(len(c.content) <= 300 + 60 for c in chunks)  # heading may add a little
    assert all(c.content.startswith("## Long section") for c in chunks)


def test_chunks_are_numbered_in_order() -> None:
    chunks = chunk_text("hours.md", MARKDOWN, min_chars=50)

    assert [c.index for c in chunks] == list(range(len(chunks)))
    assert all(c.source == "hours.md" for c in chunks)


def test_empty_text_produces_no_chunks() -> None:
    assert chunk_text("empty.txt", "   \n\n ") == []
