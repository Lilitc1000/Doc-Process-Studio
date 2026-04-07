import re
from functools import lru_cache
from pathlib import Path

from ...models.skill.runtime import SkillContextChunk, SkillContextChunkSummary
from ...settings import settings
from .registry import SKILLS_DIR, get_skill_interface

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")
TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]{1,8}|[a-zA-Z0-9_-]{2,}")


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def _iter_skill_source_files(skill_id: str) -> list[Path]:
    skill_dir = SKILLS_DIR / skill_id
    candidate_paths: list[Path] = []

    skill_markdown = skill_dir / "SKILL.md"
    if skill_markdown.is_file():
        candidate_paths.append(skill_markdown)

    references_dir = skill_dir / "references"
    if references_dir.is_dir():
        for file_path in sorted(references_dir.rglob("*")):
            if file_path.is_file():
                candidate_paths.append(file_path)

    return candidate_paths


def _split_markdown_sections(file_path: Path) -> list[tuple[str, str]]:
    raw_text = file_path.read_text(encoding="utf-8")
    if not raw_text.strip():
        return []

    sections: list[tuple[str, str]] = []
    current_title = file_path.stem
    current_lines: list[str] = []

    for line in raw_text.splitlines():
        heading_match = HEADING_PATTERN.match(line.strip())
        if heading_match:
            content = _normalize_whitespace("\n".join(current_lines))
            if content:
                sections.append((current_title, content))
            current_title = heading_match.group(2).strip() or file_path.stem
            current_lines = []
            continue

        current_lines.append(line)

    trailing_content = _normalize_whitespace("\n".join(current_lines))
    if trailing_content:
        sections.append((current_title, trailing_content))

    return sections


def _split_large_section(title: str, content: str) -> list[tuple[str, str]]:
    max_characters = settings.skill_chunk_max_characters
    if len(content) <= max_characters:
        return [(title, content)]

    paragraphs = [paragraph.strip() for paragraph in content.split("\n\n")]
    chunks: list[tuple[str, str]] = []
    current_parts: list[str] = []
    current_length = 0
    chunk_index = 1

    for paragraph in paragraphs:
        if not paragraph:
            continue

        projected_length = current_length + len(paragraph) + (2 if current_parts else 0)
        if current_parts and projected_length > max_characters:
            chunks.append((f"{title}（片段 {chunk_index}）", "\n\n".join(current_parts)))
            chunk_index += 1
            current_parts = [paragraph]
            current_length = len(paragraph)
            continue

        current_parts.append(paragraph)
        current_length = projected_length

    if current_parts:
        chunks.append((f"{title}（片段 {chunk_index}）", "\n\n".join(current_parts)))

    return chunks


@lru_cache(maxsize=32)
def load_skill_context_chunks(skill_id: str) -> list[SkillContextChunk]:
    get_skill_interface(skill_id)

    chunks: list[SkillContextChunk] = []
    for file_path in _iter_skill_source_files(skill_id):
        relative_path = file_path.relative_to(SKILLS_DIR / skill_id).as_posix()
        for section_index, (title, content) in enumerate(
            _split_markdown_sections(file_path),
            start=1,
        ):
            for chunk_offset, (chunk_title, chunk_content) in enumerate(
                _split_large_section(title, content),
                start=1,
            ):
                preview = chunk_content[:120].replace("\n", " ").strip()
                chunks.append(
                    SkillContextChunk(
                        id=f"{relative_path}::{section_index}:{chunk_offset}",
                        skill_id=skill_id,
                        source_path=relative_path,
                        title=chunk_title,
                        preview=preview,
                        content=chunk_content,
                    )
                )

    return chunks


def list_skill_context_chunk_summaries(
    skill_id: str,
) -> list[SkillContextChunkSummary]:
    return [
        SkillContextChunkSummary(
            id=chunk.id,
            source_path=chunk.source_path,
            title=chunk.title,
            preview=chunk.preview,
        )
        for chunk in load_skill_context_chunks(skill_id)
    ]


def get_skill_context_chunks_by_ids(
    skill_id: str,
    chunk_ids: list[str],
) -> list[SkillContextChunk]:
    chunk_map = {chunk.id: chunk for chunk in load_skill_context_chunks(skill_id)}
    return [chunk_map[chunk_id] for chunk_id in chunk_ids if chunk_id in chunk_map]


def _extract_query_tokens(query: str) -> list[str]:
    unique_tokens: list[str] = []
    for token in TOKEN_PATTERN.findall(query.lower()):
        cleaned = token.strip()
        if cleaned and cleaned not in unique_tokens:
            unique_tokens.append(cleaned)
    return unique_tokens


def search_skill_context_chunks(
    skill_id: str,
    query: str,
    exclude_chunk_ids: set[str] | None = None,
    limit: int | None = None,
    source_path_contains: str | None = None,
) -> list[SkillContextChunk]:
    normalized_excludes = exclude_chunk_ids or set()
    query_tokens = _extract_query_tokens(query)
    if not query_tokens:
        return []

    scored_chunks: list[tuple[int, SkillContextChunk]] = []
    for chunk in load_skill_context_chunks(skill_id):
        if chunk.id in normalized_excludes:
            continue

        if source_path_contains and source_path_contains.lower() not in chunk.source_path.lower():
            continue

        haystack = "\n".join(
            [
                chunk.title.lower(),
                chunk.source_path.lower(),
                chunk.preview.lower(),
                chunk.content.lower(),
            ]
        )
        score = 0
        title_lower = chunk.title.lower()
        source_path_lower = chunk.source_path.lower()
        preview_lower = chunk.preview.lower()
        content_lower = chunk.content.lower()

        for token in query_tokens:
            if token in source_path_lower:
                score += 5
            if token in title_lower:
                score += 4
            if token in preview_lower:
                score += 2
            if token in content_lower:
                score += 1

        if score > 0:
            scored_chunks.append((score, chunk))

    scored_chunks.sort(
        key=lambda item: (-item[0], item[1].source_path, item[1].title, item[1].id)
    )
    final_limit = limit or settings.skill_context_search_limit
    return [chunk for _, chunk in scored_chunks[:final_limit]]
