import logging

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PayloadSchemaType, VectorParams

from .config import settings

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url)
    return _client


def ensure_knowledge_base_collection() -> None:
    client = get_qdrant_client()
    collection_name = settings.kb_collection_name
    collections = client.get_collections().collections
    collection_names = {c.name for c in collections}

    if collection_name in collection_names:
        logger.info("Qdrant collection '%s' already exists.", collection_name)
        return

    logger.info("Creating Qdrant collection '%s'...", collection_name)
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )

    client.create_payload_index(
        collection_name=collection_name,
        field_name="project_name",
        field_schema=PayloadSchemaType.KEYWORD,
    )
    client.create_payload_index(
        collection_name=collection_name,
        field_name="document_id",
        field_schema=PayloadSchemaType.KEYWORD,
    )
    client.create_payload_index(
        collection_name=collection_name,
        field_name="is_latest",
        field_schema=PayloadSchemaType.BOOL,
    )
    client.create_payload_index(
        collection_name=collection_name,
        field_name="file_type",
        field_schema=PayloadSchemaType.KEYWORD,
    )
    client.create_payload_index(
        collection_name=collection_name,
        field_name="content_type",
        field_schema=PayloadSchemaType.KEYWORD,
    )
    logger.info("Qdrant collection '%s' created with payload indexes.", collection_name)
