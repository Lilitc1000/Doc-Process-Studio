import re
from dataclasses import dataclass

from ...core.config import settings


@dataclass
class TextChunk:
    content: str
    page_number: int | None = None
    section_title: str | None = None
    sheet_name: str | None = None
    chunk_index: int = 0


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def chunk_text(
    text: str,
    *,
    page_number: int | None = None,
    section_title: str | None = None,
    sheet_name: str | None = None,
    max_characters: int | None = None,
) -> list[TextChunk]:
    limit = max_characters or settings.kb_chunk_max_characters
    normalized = _normalize_whitespace(text)
    if not normalized:
        return []

    if len(normalized) <= limit:
        return [TextChunk(
            content=normalized,
            page_number=page_number,
            section_title=section_title,
            sheet_name=sheet_name,
            chunk_index=0,
        )]

    paragraphs = [p.strip() for p in normalized.split("\n\n")]
    chunks: list[TextChunk] = []
    current_parts: list[str] = []
    current_length = 0
    chunk_index = 0

    for paragraph in paragraphs:
        if not paragraph:
            continue
        projected_length = current_length + len(paragraph) + (2 if current_parts else 0)
        if current_parts and projected_length > limit:
            chunks.append(TextChunk(
                content="\n\n".join(current_parts),
                page_number=page_number,
                section_title=section_title,
                sheet_name=sheet_name,
                chunk_index=chunk_index,
            ))
            chunk_index += 1
            current_parts = [paragraph]
            current_length = len(paragraph)
            continue
        current_parts.append(paragraph)
        current_length = projected_length

    if current_parts:
        chunks.append(TextChunk(
            content="\n\n".join(current_parts),
            page_number=page_number,
            section_title=section_title,
            sheet_name=sheet_name,
            chunk_index=chunk_index,
        ))

    return chunks
