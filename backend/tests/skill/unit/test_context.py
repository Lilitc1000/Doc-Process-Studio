from typing import Any

from doc_process_studio.skill.application.dtos.runtime import SkillContextChunk
from doc_process_studio.skill.infrastructure.context import (
    _build_chunk_embedding_fingerprint,
    _cosine_similarity,
    _extract_embeddings_from_embed_payload,
    _extract_query_tokens,
    _normalize_whitespace,
    _parse_rerank_json_object,
    _rank_to_reciprocal_score,
)


def test_normalize_whitespace() -> None:
    assert _normalize_whitespace("a\n\n\nb") == "a\n\nb"


def test_normalize_whitespace_strips() -> None:
    assert _normalize_whitespace("  hello  ") == "hello"


def test_extract_query_tokens() -> None:
    tokens = _extract_query_tokens("交通行业经验 traffic industry")
    assert "交通行业经验" in tokens
    assert "traffic" in tokens


def test_extract_query_tokens_dedup() -> None:
    tokens = _extract_query_tokens("test test test")
    assert tokens.count("test") == 1


def test_extract_query_tokens_empty() -> None:
    assert _extract_query_tokens("") == []


def test_cosine_similarity_identical() -> None:
    assert abs(_cosine_similarity([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-6


def test_cosine_similarity_orthogonal() -> None:
    assert abs(_cosine_similarity([1.0, 0.0], [0.0, 1.0])) < 1e-6


def test_cosine_similarity_empty() -> None:
    assert _cosine_similarity([], []) == 0.0


def test_cosine_similarity_different_length() -> None:
    assert _cosine_similarity([1.0], [1.0, 2.0]) == 0.0


def test_extract_embeddings_from_embed_payload_embeddings_key() -> None:
    payload = {"embeddings": [[1.0, 2.0], [3.0, 4.0]]}
    result = _extract_embeddings_from_embed_payload(payload)
    assert result is not None
    assert len(result) == 2


def test_extract_embeddings_from_embed_payload_single() -> None:
    payload = {"embedding": [1.0, 2.0]}
    result = _extract_embeddings_from_embed_payload(payload)
    assert result is not None
    assert len(result) == 1


def test_extract_embeddings_from_embed_payload_empty() -> None:
    payload: dict[str, Any] = {"embeddings": []}
    result = _extract_embeddings_from_embed_payload(payload)
    assert result is None


def test_extract_embeddings_from_embed_payload_invalid() -> None:
    result = _extract_embeddings_from_embed_payload({"not": "a valid embed payload"})
    assert result is None


def test_build_chunk_embedding_fingerprint() -> None:
    chunks = [
        SkillContextChunk(
            id="c1",
            skill_id="s1",
            source_path="ref.md",
            title="T1",
            preview="p1",
            content="content1",
        ),
        SkillContextChunk(
            id="c2",
            skill_id="s1",
            source_path="ref.md",
            title="T2",
            preview="p2",
            content="content2",
        ),
    ]
    fp1 = _build_chunk_embedding_fingerprint(chunks)
    fp2 = _build_chunk_embedding_fingerprint(chunks)
    assert fp1 == fp2


def test_build_chunk_embedding_fingerprint_different() -> None:
    chunks1 = [
        SkillContextChunk(
            id="c1",
            skill_id="s1",
            source_path="ref.md",
            title="T1",
            preview="p1",
            content="content1",
        ),
    ]
    chunks2 = [
        SkillContextChunk(
            id="c2",
            skill_id="s1",
            source_path="ref.md",
            title="T2",
            preview="p2",
            content="content2",
        ),
    ]
    fp1 = _build_chunk_embedding_fingerprint(chunks1)
    fp2 = _build_chunk_embedding_fingerprint(chunks2)
    assert fp1 != fp2


def test_rank_to_reciprocal_score() -> None:
    assert _rank_to_reciprocal_score(0) > _rank_to_reciprocal_score(1)
    assert _rank_to_reciprocal_score(1) > _rank_to_reciprocal_score(2)


def test_parse_rerank_json_object_valid() -> None:
    result = _parse_rerank_json_object('{"ranked": [{"id": "c1", "relevance": 0.9}]}')
    assert result is not None
    assert "ranked" in result


def test_parse_rerank_json_object_invalid() -> None:
    assert _parse_rerank_json_object("not json") is None


def test_parse_rerank_json_object_empty() -> None:
    assert _parse_rerank_json_object("") is None


def test_parse_rerank_json_object_embedded() -> None:
    result = _parse_rerank_json_object('some text {"ranked": []} more text')
    assert result is not None
    assert "ranked" in result
