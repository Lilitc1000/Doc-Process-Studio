import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from ...models.skill.runtime import SkillContextChunk, SkillContextChunkSummary
from ...settings import settings
from ..infra.dtutils import utcnow
from ..infra.ollama_client import (
    build_timeout,
    get_ollama_base_url,
)
from .registry import SKILLS_DIR, get_skill_interface

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")
TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]{1,8}|[a-zA-Z0-9_-]{2,}")

_EMBEDDING_CACHE: dict[tuple[str, str], tuple[str, datetime, dict[str, list[float]]]] = {}
_QUERY_EMBEDDING_CACHE: dict[tuple[str, str], tuple[datetime, list[float]]] = {}


@dataclass
class _LexicalChunkDoc:
    chunk_id: str
    tf: dict[str, int]
    length: int


@dataclass
class _LexicalIndex:
    docs: list[_LexicalChunkDoc]
    df: dict[str, int]
    avg_doc_length: float


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


def _tokenize_chunk(chunk: SkillContextChunk) -> list[str]:
    raw_text = "\n".join(
        [
            chunk.title,
            chunk.source_path,
            chunk.preview,
            chunk.content,
        ]
    ).lower()
    return [token.strip() for token in TOKEN_PATTERN.findall(raw_text) if token.strip()]


@lru_cache(maxsize=32)
def _build_lexical_index(skill_id: str) -> _LexicalIndex:
    docs: list[_LexicalChunkDoc] = []
    df: dict[str, int] = {}

    for chunk in load_skill_context_chunks(skill_id):
        tokens = _tokenize_chunk(chunk)
        tf: dict[str, int] = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1

        docs.append(
            _LexicalChunkDoc(
                chunk_id=chunk.id,
                tf=tf,
                length=max(1, len(tokens)),
            )
        )
        for token in tf.keys():
            df[token] = df.get(token, 0) + 1

    avg_doc_length = (
        sum(doc.length for doc in docs) / len(docs)
        if docs
        else 1.0
    )
    return _LexicalIndex(docs=docs, df=df, avg_doc_length=max(avg_doc_length, 1.0))


def _compute_bm25_score(
    *,
    query_tokens: list[str],
    doc: _LexicalChunkDoc,
    index: _LexicalIndex,
) -> float:
    # BM25 常见参数
    k1 = 1.2
    b = 0.75
    total_docs = max(1, len(index.docs))

    score = 0.0
    for token in query_tokens:
        tf = doc.tf.get(token, 0)
        if tf <= 0:
            continue
        df = index.df.get(token, 0)
        idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
        denominator = tf + k1 * (1 - b + b * (doc.length / index.avg_doc_length))
        score += idf * ((tf * (k1 + 1)) / max(1e-6, denominator))

    return score


def _rank_to_reciprocal_score(rank: int) -> float:
    return 1.0 / (rank + 1.5)


def _embedding_cache_ttl() -> timedelta:
    return timedelta(seconds=max(60, settings.skill_retrieval_embedding_cache_ttl_seconds))


def _build_chunk_embedding_fingerprint(chunks: list[SkillContextChunk]) -> str:
    digest = hashlib.sha256()
    for chunk in chunks:
        digest.update(chunk.id.encode("utf-8"))
        digest.update(chunk.source_path.encode("utf-8"))
        digest.update(str(len(chunk.content)).encode("utf-8"))
    return digest.hexdigest()


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for index, left_value in enumerate(left):
        right_value = right[index]
        numerator += left_value * right_value
        left_norm += left_value * left_value
        right_norm += right_value * right_value
    if left_norm <= 0 or right_norm <= 0:
        return 0.0
    return numerator / math.sqrt(left_norm * right_norm)


def _extract_embeddings_from_embed_payload(payload: Any) -> list[list[float]] | None:
    if not isinstance(payload, dict):
        return None
    embeddings = payload.get("embeddings")
    if isinstance(embeddings, list) and embeddings:
        normalized: list[list[float]] = []
        for item in embeddings:
            if isinstance(item, list):
                normalized_vector = [float(value) for value in item if isinstance(value, (int, float))]
                if normalized_vector:
                    normalized.append(normalized_vector)
        return normalized or None

    single_embedding = payload.get("embedding")
    if isinstance(single_embedding, list):
        normalized_vector = [float(value) for value in single_embedding if isinstance(value, (int, float))]
        if normalized_vector:
            return [normalized_vector]

    return None


def _post_embed_with_ollama(
    *,
    model: str,
    texts: list[str],
) -> list[list[float]] | None:
    if not texts:
        return []

    try:
        base_url = get_ollama_base_url()
    except Exception:
        return None

    embed_url = f"{base_url}/api/embed"
    embeddings_url = f"{base_url}/api/embeddings"
    timeout = build_timeout()

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                embed_url,
                json={
                    "model": model,
                    "input": texts,
                },
            )
            response.raise_for_status()
            payload = response.json()
            parsed = _extract_embeddings_from_embed_payload(payload)
            if parsed and len(parsed) == len(texts):
                return parsed
    except Exception:
        pass

    # 兼容旧接口：逐条走 /api/embeddings
    fallback_embeddings: list[list[float]] = []
    try:
        with httpx.Client(timeout=timeout) as client:
            for text in texts:
                response = client.post(
                    embeddings_url,
                    json={
                        "model": model,
                        "prompt": text,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                parsed = _extract_embeddings_from_embed_payload(payload)
                if not parsed:
                    return None
                fallback_embeddings.append(parsed[0])
    except Exception:
        return None

    return fallback_embeddings if len(fallback_embeddings) == len(texts) else None


def _build_embedding_text(chunk: SkillContextChunk) -> str:
    return "\n".join(
        [
            f"标题：{chunk.title}",
            f"路径：{chunk.source_path}",
            "内容：",
            chunk.content[: min(1200, len(chunk.content))],
        ]
    )


def _resolve_embedding_model() -> str:
    configured = settings.skill_retrieval_embedding_model.strip()
    return configured or "nomic-embed-text"


def _get_query_embedding(
    *,
    embedding_model: str,
    query: str,
) -> list[float] | None:
    cache_key = (embedding_model, query.strip())
    cached = _QUERY_EMBEDDING_CACHE.get(cache_key)
    if cached is not None:
        cached_at, cached_vector = cached
        if utcnow() - cached_at <= _embedding_cache_ttl():
            return cached_vector

    embedding_payload = _post_embed_with_ollama(
        model=embedding_model,
        texts=[query],
    )
    if not embedding_payload:
        return None

    vector = embedding_payload[0]
    _QUERY_EMBEDDING_CACHE[cache_key] = (utcnow(), vector)
    return vector


def _get_chunk_embeddings(
    *,
    skill_id: str,
    chunks: list[SkillContextChunk],
    embedding_model: str,
) -> dict[str, list[float]] | None:
    cache_key = (skill_id, embedding_model)
    fingerprint = _build_chunk_embedding_fingerprint(chunks)
    cached = _EMBEDDING_CACHE.get(cache_key)
    if cached is not None:
        cached_fingerprint, cached_at, cached_vectors = cached
        if cached_fingerprint == fingerprint and utcnow() - cached_at <= _embedding_cache_ttl():
            return cached_vectors

    batch_size = max(1, settings.skill_retrieval_embedding_batch_size)
    vectors_by_id: dict[str, list[float]] = {}
    for start_index in range(0, len(chunks), batch_size):
        batch_chunks = chunks[start_index : start_index + batch_size]
        batch_texts = [_build_embedding_text(chunk) for chunk in batch_chunks]
        batch_vectors = _post_embed_with_ollama(
            model=embedding_model,
            texts=batch_texts,
        )
        if not batch_vectors or len(batch_vectors) != len(batch_chunks):
            return None

        for index, chunk in enumerate(batch_chunks):
            vectors_by_id[chunk.id] = batch_vectors[index]

    _EMBEDDING_CACHE[cache_key] = (fingerprint, utcnow(), vectors_by_id)
    return vectors_by_id


def _parse_rerank_json_object(raw_text: str) -> dict[str, Any] | None:
    normalized = raw_text.strip()
    if not normalized:
        return None

    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        return parsed

    object_match = re.search(r"\{[\s\S]*\}", normalized)
    if object_match is None:
        return None

    try:
        parsed = json.loads(object_match.group(0))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _rerank_chunks_with_model(
    *,
    query: str,
    candidates: list[SkillContextChunk],
    reranker_model: str,
) -> dict[str, float] | None:
    if not candidates:
        return {}

    try:
        base_url = get_ollama_base_url()
    except Exception:
        return None

    chat_url = f"{base_url}/api/chat"
    system_prompt = (
        "你是检索重排序器。"
        "请根据用户问题对候选片段按相关性打分。"
        "只输出 JSON 对象，不要附加说明文字。"
    )
    candidate_lines = []
    for chunk in candidates:
        candidate_lines.append(
            {
                "id": chunk.id,
                "source_path": chunk.source_path,
                "title": chunk.title,
                "preview": chunk.preview[:180],
            }
        )

    user_prompt = json.dumps(
        {
            "query": query,
            "candidates": candidate_lines,
            "output_schema": {
                "ranked": [
                    {"id": "chunk-id", "relevance": 0.0}
                ]
            },
        },
        ensure_ascii=False,
    )

    payload = {
        "model": reranker_model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    try:
        with httpx.Client(timeout=build_timeout()) as client:
            response = client.post(chat_url, json=payload)
            response.raise_for_status()
            response_payload = response.json()
    except Exception:
        return None

    message = response_payload.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, str):
        return None

    parsed = _parse_rerank_json_object(content)
    if not isinstance(parsed, dict):
        return None

    ranked = parsed.get("ranked")
    if not isinstance(ranked, list):
        return None

    relevance_map: dict[str, float] = {}
    for item in ranked:
        if not isinstance(item, dict):
            continue
        chunk_id = item.get("id")
        relevance = item.get("relevance")
        if not isinstance(chunk_id, str):
            continue
        if not isinstance(relevance, (int, float)):
            continue
        relevance_map[chunk_id.strip()] = max(0.0, min(1.0, float(relevance)))

    return relevance_map or None


def search_skill_context_chunks(
    skill_id: str,
    query: str,
    exclude_chunk_ids: set[str] | None = None,
    limit: int | None = None,
    source_path_contains: str | None = None,
    reranker_model: str | None = None,
) -> list[SkillContextChunk]:
    normalized_excludes = exclude_chunk_ids or set()
    query_tokens = _extract_query_tokens(query)
    if not query_tokens:
        return []

    all_chunks = load_skill_context_chunks(skill_id)
    filtered_chunks: list[SkillContextChunk] = []
    for chunk in all_chunks:
        if chunk.id in normalized_excludes:
            continue
        if source_path_contains and source_path_contains.lower() not in chunk.source_path.lower():
            continue
        filtered_chunks.append(chunk)

    if not filtered_chunks:
        return []

    lexical_index = _build_lexical_index(skill_id)
    docs_by_chunk_id = {doc.chunk_id: doc for doc in lexical_index.docs}
    lexical_scored: list[tuple[float, SkillContextChunk]] = []
    for chunk in filtered_chunks:
        doc = docs_by_chunk_id.get(chunk.id)
        if doc is None:
            continue
        score = _compute_bm25_score(
            query_tokens=query_tokens,
            doc=doc,
            index=lexical_index,
        )
        if score > 0:
            lexical_scored.append((score, chunk))
    lexical_scored.sort(
        key=lambda item: (-item[0], item[1].source_path, item[1].title, item[1].id)
    )

    lexical_limit = max(4, settings.skill_retrieval_lexical_candidate_limit)
    lexical_candidates = lexical_scored[:lexical_limit]

    semantic_candidates: list[tuple[float, SkillContextChunk]] = []
    if settings.skill_retrieval_semantic_enabled:
        embedding_model = _resolve_embedding_model()
        query_vector = _get_query_embedding(
            embedding_model=embedding_model,
            query=query,
        )
        chunk_vectors = _get_chunk_embeddings(
            skill_id=skill_id,
            chunks=filtered_chunks,
            embedding_model=embedding_model,
        )
        if query_vector and chunk_vectors:
            for chunk in filtered_chunks:
                chunk_vector = chunk_vectors.get(chunk.id)
                if not chunk_vector:
                    continue
                similarity = _cosine_similarity(query_vector, chunk_vector)
                if similarity > 0:
                    semantic_candidates.append((similarity, chunk))
            semantic_candidates.sort(
                key=lambda item: (-item[0], item[1].source_path, item[1].title, item[1].id)
            )
            semantic_candidates = semantic_candidates[
                : max(4, settings.skill_retrieval_semantic_candidate_limit)
            ]

    merged_scores: dict[str, float] = {}
    chunk_map = {chunk.id: chunk for chunk in filtered_chunks}
    for rank, (score, chunk) in enumerate(lexical_candidates):
        del score
        merged_scores[chunk.id] = merged_scores.get(chunk.id, 0.0) + _rank_to_reciprocal_score(rank)
    for rank, (score, chunk) in enumerate(semantic_candidates):
        del score
        merged_scores[chunk.id] = merged_scores.get(chunk.id, 0.0) + _rank_to_reciprocal_score(rank)

    candidate_ids = [
        chunk_id
        for chunk_id, _score in sorted(
            merged_scores.items(),
            key=lambda item: -item[1],
        )
    ]
    if not candidate_ids:
        candidate_ids = [chunk.id for _score, chunk in lexical_candidates]

    rerank_candidates = [
        chunk_map[chunk_id]
        for chunk_id in candidate_ids
        if chunk_id in chunk_map
    ][: max(4, settings.skill_retrieval_rerank_candidate_limit)]

    final_ranked_chunks = rerank_candidates
    if settings.skill_retrieval_rerank_enabled and rerank_candidates:
        reranker = (reranker_model or "").strip()
        if reranker:
            relevance_map = _rerank_chunks_with_model(
                query=query,
                candidates=rerank_candidates,
                reranker_model=reranker,
            )
            if relevance_map:
                final_ranked_chunks = sorted(
                    rerank_candidates,
                    key=lambda chunk: (
                        -relevance_map.get(chunk.id, 0.0),
                        -merged_scores.get(chunk.id, 0.0),
                        chunk.source_path,
                        chunk.title,
                        chunk.id,
                    ),
                )

    final_limit = limit or settings.skill_context_search_limit
    return final_ranked_chunks[:final_limit]
