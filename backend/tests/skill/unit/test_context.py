from doc_process_studio.skill.service.context import (
    _build_chunk_embedding_fingerprint,
    _cosine_similarity,
    _extract_embeddings_from_embed_payload,
    _extract_query_tokens,
    _normalize_whitespace,
    _parse_rerank_json_object,
    _rank_to_reciprocal_score,
)
from doc_process_studio.skill.models.runtime import SkillContextChunk


def test_normalize_whitespace():
    assert _normalize_whitespace("a\n\n\nb") == "a\n\nb"


def test_normalize_whitespace_strips():
    assert _normalize_whitespace("  hello  ") == "hello"


def test_extract_query_tokens():
    tokens = _extract_query_tokens("交通行业经验 traffic industry")
    assert "交通行业经验" in tokens
    assert "traffic" in tokens


def test_extract_query_tokens_dedup():
    tokens = _extract_query_tokens("test test test")
    assert tokens.count("test") == 1


def test_extract_query_tokens_empty():
    assert _extract_query_tokens("") == []


def test_cosine_similarity_identical():
    assert abs(_cosine_similarity([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-6


def test_cosine_similarity_orthogonal():
    assert abs(_cosine_similarity([1.0, 0.0], [0.0, 1.0])) < 1e-6


def test_cosine_similarity_empty():
    assert _cosine_similarity([], []) == 0.0


def test_cosine_similarity_different_length():
    assert _cosine_similarity([1.0], [1.0, 2.0]) == 0.0


def test_extract_embeddings_from_embed_payload_embeddings_key():
    payload = {"embeddings": [[1.0, 2.0], [3.0, 4.0]]}
    result = _extract_embeddings_from_embed_payload(payload)
    assert result is not None
    assert len(result) == 2


def test_extract_embeddings_from_embed_payload_single():
    payload = {"embedding": [1.0, 2.0]}
    result = _extract_embeddings_from_embed_payload(payload)
    assert result is not None
    assert len(result) == 1


def test_extract_embeddings_from_embed_payload_empty():
    payload = {"embeddings": []}
    result = _extract_embeddings_from_embed_payload(payload)
    assert result is None


def test_extract_embeddings_from_embed_payload_invalid():
    result = _extract_embeddings_from_embed_payload("not a dict")
    assert result is None


def test_build_chunk_embedding_fingerprint():
    chunks = [
        SkillContextChunk(
            id="c1", skill_id="s1", source_path="ref.md",
            title="T1", preview="p1", content="content1",
        ),
        SkillContextChunk(
            id="c2", skill_id="s1", source_path="ref.md",
            title="T2", preview="p2", content="content2",
        ),
    ]
    fp1 = _build_chunk_embedding_fingerprint(chunks)
    fp2 = _build_chunk_embedding_fingerprint(chunks)
    assert fp1 == fp2


def test_build_chunk_embedding_fingerprint_different():
    chunks1 = [
        SkillContextChunk(
            id="c1", skill_id="s1", source_path="ref.md",
            title="T1", preview="p1", content="content1",
        ),
    ]
    chunks2 = [
        SkillContextChunk(
            id="c2", skill_id="s1", source_path="ref.md",
            title="T2", preview="p2", content="content2",
        ),
    ]
    fp1 = _build_chunk_embedding_fingerprint(chunks1)
    fp2 = _build_chunk_embedding_fingerprint(chunks2)
    assert fp1 != fp2


def test_rank_to_reciprocal_score():
    assert _rank_to_reciprocal_score(0) > _rank_to_reciprocal_score(1)
    assert _rank_to_reciprocal_score(1) > _rank_to_reciprocal_score(2)


def test_parse_rerank_json_object_valid():
    result = _parse_rerank_json_object('{"ranked": [{"id": "c1", "relevance": 0.9}]}')
    assert result is not None
    assert "ranked" in result


def test_parse_rerank_json_object_invalid():
    assert _parse_rerank_json_object("not json") is None


def test_parse_rerank_json_object_empty():
    assert _parse_rerank_json_object("") is None


def test_parse_rerank_json_object_embedded():
    result = _parse_rerank_json_object('some text {"ranked": []} more text')
    assert result is not None
    assert "ranked" in result
