import logging
import uuid
from collections.abc import Sequence

from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
)

from ...common.infrastructure.config import settings
from ...common.infrastructure.qdrant import get_qdrant_client
from ..application.dtos import KBChunkPayload

logger = logging.getLogger(__name__)


def _build_point_id() -> str:
    return uuid.uuid4().hex


def upsert_chunks(
    chunks: Sequence[KBChunkPayload],
    vectors: Sequence[list[float]],
) -> int:
    if len(chunks) != len(vectors):
        logger.error("Chunks and vectors length mismatch: %d vs %d", len(chunks), len(vectors))
        return 0

    client = get_qdrant_client()
    collection_name = settings.kb_collection_name
    points: list[PointStruct] = []

    for chunk, vector in zip(chunks, vectors, strict=False):
        point = PointStruct(
            id=_build_point_id(),
            vector=vector,
            payload=chunk.model_dump(),
        )
        points.append(point)

    if points:
        client.upsert(collection_name=collection_name, points=points)

    return len(points)


def delete_document_vectors(document_id: str) -> int:
    client = get_qdrant_client()
    collection_name = settings.kb_collection_name
    client.delete(
        collection_name=collection_name,
        points_selector=Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))],
        ),
    )
    return 0


def delete_project_vectors(project_name: str) -> int:
    client = get_qdrant_client()
    collection_name = settings.kb_collection_name
    client.delete(
        collection_name=collection_name,
        points_selector=Filter(
            must=[FieldCondition(key="project_name", match=MatchValue(value=project_name))],
        ),
    )
    return 0


def search_knowledge_base(
    project_name: str,
    query_vector: list[float],
    top_k: int | None = None,
) -> list[dict]:
    client = get_qdrant_client()
    collection_name = settings.kb_collection_name
    k = top_k or settings.kb_search_top_k

    response = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        query_filter=Filter(
            must=[
                FieldCondition(key="project_name", match=MatchValue(value=project_name)),
                FieldCondition(key="is_latest", match=MatchValue(value=True)),
            ],
        ),
        limit=k,
        with_payload=True,
    )

    return [
        {
            "score": hit.score,
            "payload": hit.payload,
        }
        for hit in response.points
    ]
