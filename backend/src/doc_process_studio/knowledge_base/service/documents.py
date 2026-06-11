import hashlib
import logging
from pathlib import PurePosixPath

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import KBDocument, KBFolder, KBProject
from ..schemas import KBChunkPayload, KBDocumentResponse
from .chunker import TextChunk, chunk_text
from .embedding import embed_texts
from .parser import extract_archive, parse_docx, parse_pdf, parse_xlsx
from .qdrant_service import delete_document_vectors, upsert_chunks

logger = logging.getLogger(__name__)


def _compute_content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _detect_file_type(file_name: str) -> str:
    ext = PurePosixPath(file_name).suffix.lower()
    type_map = {".pdf": "pdf", ".docx": "docx", ".doc": "docx", ".xlsx": "xlsx", ".xls": "xlsx"}
    return type_map.get(ext, "")


async def upload_document(
    db: AsyncSession,
    project_id: str,
    folder_id: str | None,
    file_name: str,
    file_bytes: bytes,
) -> KBDocumentResponse | None:
    project_stmt = select(KBProject).where(KBProject.id == project_id)
    project_result = await db.execute(project_stmt)
    project = project_result.scalar_one_or_none()
    if not project:
        return None

    if folder_id:
        folder_stmt = select(KBFolder).where(KBFolder.id == folder_id, KBFolder.project_id == project_id)
        folder_result = await db.execute(folder_stmt)
        if not folder_result.scalar_one_or_none():
            return None

    file_type = _detect_file_type(file_name)
    is_archive = PurePosixPath(file_name).suffix.lower() in {".zip", ".rar", ".7z"}

    if is_archive:
        return await _handle_archive_upload(db, project_id, folder_id, file_name, file_bytes, project.name)

    if not file_type:
        logger.info("Ignoring unsupported file: %s", file_name)
        return None

    content_hash = _compute_content_hash(file_bytes)

    existing_stmt = select(KBDocument).where(
        KBDocument.project_id == project_id,
        KBDocument.folder_id == folder_id,
        KBDocument.file_name == file_name,
        KBDocument.is_latest.is_(True),
    )
    existing_result = await db.execute(existing_stmt)
    existing_doc = existing_result.scalar_one_or_none()

    version = 1
    if existing_doc:
        if existing_doc.content_hash == content_hash:
            return KBDocumentResponse.model_validate(existing_doc)
        existing_doc.is_latest = False
        version = existing_doc.version + 1

    doc = KBDocument(
        project_id=project_id,
        folder_id=folder_id,
        file_name=file_name,
        file_type=file_type,
        file_size=len(file_bytes),
        content_hash=content_hash,
        version=version,
        is_latest=True,
        is_indexed=False,
    )
    db.add(doc)
    await db.flush()
    return KBDocumentResponse.model_validate(doc)


async def _handle_archive_upload(
    db: AsyncSession,
    project_id: str,
    folder_id: str | None,
    archive_name: str,
    file_bytes: bytes,
    project_name: str,
) -> KBDocumentResponse | None:
    extracted_files = extract_archive(file_bytes, archive_name)
    if not extracted_files:
        logger.info("No supported files found in archive: %s", archive_name)
        return None

    archive_folder_name = PurePosixPath(archive_name).stem
    from .folders import create_folder
    archive_folder = await create_folder(db, project_id, archive_folder_name, folder_id)
    if not archive_folder:
        return None

    created_docs: list[KBDocumentResponse] = []
    folder_cache: dict[str, str] = {}

    for extracted in extracted_files:
        parent_folder_id = archive_folder.id
        parent_path_parts = PurePosixPath(extracted.relative_path).parent.parts

        if len(parent_path_parts) > 0:
            current_parent_id: str | None = archive_folder.id
            for part in parent_path_parts:
                cache_key = f"{current_parent_id}:{part}"
                if cache_key in folder_cache:
                    current_parent_id = folder_cache[cache_key]
                    continue
                sub_folder = await create_folder(db, project_id, part, current_parent_id)
                if sub_folder:
                    folder_cache[cache_key] = sub_folder.id
                    current_parent_id = sub_folder.id
            parent_folder_id = current_parent_id or archive_folder.id

        doc = await upload_document(
            db, project_id, parent_folder_id, extracted.file_name, extracted.file_bytes,
        )
        if doc and not doc.is_indexed:
            chunk_count = await index_document(db, doc.id, project_name, extracted.file_bytes)
            doc.is_indexed = True
            doc.chunk_count = chunk_count
        if doc:
            created_docs.append(doc)

    content_hash = _compute_content_hash(file_bytes)
    archive_doc = KBDocument(
        project_id=project_id,
        folder_id=folder_id,
        file_name=archive_name,
        file_type="archive",
        file_size=len(file_bytes),
        content_hash=content_hash,
        is_indexed=False,
        is_latest=True,
    )
    db.add(archive_doc)
    await db.flush()
    return KBDocumentResponse.model_validate(archive_doc)


async def delete_document(db: AsyncSession, document_id: str) -> bool:
    stmt = select(KBDocument).where(KBDocument.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        return False
    delete_document_vectors(document_id)
    await db.delete(doc)
    await db.flush()
    return True


async def index_document(
    db: AsyncSession,
    document_id: str,
    project_name: str,
    file_bytes: bytes,
) -> int:
    stmt = select(KBDocument).where(KBDocument.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        return 0

    if not file_bytes:
        logger.warning("Cannot index document %s: no file content provided", document_id)
        return 0

    chunks_with_meta = _parse_and_chunk(doc.file_name, doc.file_type, file_bytes)
    if not chunks_with_meta:
        doc.is_indexed = True
        await db.flush()
        return 0

    folder_path = ""
    if doc.folder_id:
        folder_stmt = select(KBFolder).where(KBFolder.id == doc.folder_id)
        folder_result = await db.execute(folder_stmt)
        folder = folder_result.scalar_one_or_none()
        if folder:
            folder_path = folder.path or ""

    chunk_payloads: list[KBChunkPayload] = []
    for chunk, meta in chunks_with_meta:
        payload = KBChunkPayload(
            project_name=project_name,
            document_id=document_id,
            file_name=doc.file_name,
            file_path=folder_path,
            file_type=doc.file_type,
            version=doc.version,
            is_latest=doc.is_latest,
            page_number=meta.get("page_number"),
            section_title=meta.get("section_title"),
            sheet_name=meta.get("sheet_name"),
            content_type=meta.get("content_type", "text"),
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            uploaded_at=doc.uploaded_at.isoformat() if doc.uploaded_at else "",
        )
        chunk_payloads.append(payload)

    texts = [c.content for c in chunk_payloads]
    vectors = await embed_texts(texts)
    count = upsert_chunks(project_name, document_id, chunk_payloads, vectors)

    doc.is_indexed = True
    doc.chunk_count = count
    await db.flush()
    return count


def _parse_and_chunk(
    file_name: str,
    file_type: str,
    file_bytes: bytes,
) -> list[tuple[TextChunk, dict]]:
    results: list[tuple[TextChunk, dict]] = []

    if file_type == "pdf":
        pages = parse_pdf(file_bytes, file_name)
        for page in pages:
            chunks = chunk_text(page.text, page_number=page.page_number)
            for c in chunks:
                results.append((c, {"page_number": page.page_number, "content_type": page.content_type}))

    elif file_type == "docx":
        sections = parse_docx(file_bytes, file_name)
        for section in sections:
            chunks = chunk_text(section.text, section_title=section.section_title)
            for c in chunks:
                results.append((c, {"section_title": section.section_title}))

    elif file_type == "xlsx":
        sheets = parse_xlsx(file_bytes, file_name)
        for sheet in sheets:
            chunks = chunk_text(sheet.text, sheet_name=sheet.sheet_name)
            for c in chunks:
                results.append((c, {"sheet_name": sheet.sheet_name}))

    return results
