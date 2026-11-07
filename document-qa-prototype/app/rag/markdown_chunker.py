import re

from app.rag.chunker import split_text


def split_markdown(
    text: str,
    chunk_size: int = 800,
    overlap: int = 120,
) -> list[str]:

    sections = re.split(
        r"(?=^#{1,6}[ \t]+)",
        text,
        flags=re.MULTILINE,
    )

    chunks = []

    for section in sections:
        section = section.strip()

        if not section:
            continue

        chunks.extend(
            split_text(
                section,
                chunk_size=chunk_size,
                overlap=overlap,
            )
        )

    return chunks