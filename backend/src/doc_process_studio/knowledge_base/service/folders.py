import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import KBFolder, KBProject
from ..schemas import KBFolderResponse, KBTreeNode, KBTreeNodeDocument, KBTreeNodeFolder

logger = logging.getLogger(__name__)


async def create_folder(
    db: AsyncSession,
    project_id: str,
    name: str,
    parent_id: str | None = None,
) -> KBFolderResponse | None:
    project_stmt = select(KBProject).where(KBProject.id == project_id)
    project_result = await db.execute(project_stmt)
    project = project_result.scalar_one_or_none()
    if not project:
        return None

    if parent_id:
        parent_stmt = select(KBFolder).where(KBFolder.id == parent_id, KBFolder.project_id == project_id)
        parent_result = await db.execute(parent_stmt)
        parent = parent_result.scalar_one_or_none()
        if not parent:
            return None
        path = f"{parent.path}/{name}"
    else:
        path = f"/{name}"

    folder = KBFolder(project_id=project_id, parent_id=parent_id, name=name, path=path)
    db.add(folder)
    await db.flush()
    return KBFolderResponse.model_validate(folder)


async def rename_folder(
    db: AsyncSession,
    folder_id: str,
    new_name: str,
) -> KBFolderResponse | None:
    stmt = select(KBFolder).where(KBFolder.id == folder_id)
    result = await db.execute(stmt)
    folder = result.scalar_one_or_none()
    if not folder:
        return None

    old_path = folder.path
    parent_path = old_path.rsplit("/", 1)[0] if "/" in old_path else ""
    new_path = f"{parent_path}/{new_name}" if parent_path else f"/{new_name}"

    folder.name = new_name
    folder.path = new_path

    child_stmt = select(KBFolder).where(KBFolder.path.like(f"{old_path}/%"))
    child_result = await db.execute(child_stmt)
    children = child_result.scalars().all()
    for child in children:
        child.path = child.path.replace(old_path, new_path, 1)

    await db.flush()
    return KBFolderResponse.model_validate(folder)


async def delete_folder(db: AsyncSession, folder_id: str) -> bool:
    stmt = select(KBFolder).where(KBFolder.id == folder_id)
    result = await db.execute(stmt)
    folder = result.scalar_one_or_none()
    if not folder:
        return False
    await db.delete(folder)
    await db.flush()
    return True


async def build_tree(db: AsyncSession, project_id: str) -> list[KBTreeNode]:
    folder_stmt = select(KBFolder).where(KBFolder.project_id == project_id).order_by(KBFolder.sort_order, KBFolder.name)
    folder_result = await db.execute(folder_stmt)
    folders = folder_result.scalars().all()

    from ..models import KBDocument
    doc_stmt = select(KBDocument).where(KBDocument.project_id == project_id).order_by(KBDocument.file_name)
    doc_result = await db.execute(doc_stmt)
    documents = doc_result.scalars().all()

    folder_nodes: dict[str, KBTreeNodeFolder] = {}
    for f in folders:
        folder_nodes[f.id] = KBTreeNodeFolder(
            id=f.id,
            name=f.name,
            path=f.path,
            sort_order=f.sort_order,
            children=[],
        )

    doc_nodes_by_folder: dict[str | None, list[KBTreeNodeDocument]] = {}
    for d in documents:
        doc_node = KBTreeNodeDocument(
            id=d.id,
            name=d.file_name,
            file_type=d.file_type,
            file_size=d.file_size,
            chunk_count=d.chunk_count,
            version=d.version,
            is_indexed=d.is_indexed,
            uploaded_at=d.uploaded_at,
        )
        doc_nodes_by_folder.setdefault(d.folder_id, []).append(doc_node)

    root_children: list[KBTreeNode] = []
    for f in folders:
        node = folder_nodes[f.id]
        if f.parent_id and f.parent_id in folder_nodes:
            folder_nodes[f.parent_id].children.append(node)
        else:
            root_children.append(node)

    for folder_id, node in folder_nodes.items():
        docs = doc_nodes_by_folder.get(folder_id, [])
        node.children.extend(docs)

    root_docs = doc_nodes_by_folder.get(None, [])
    root_children.extend(root_docs)

    return root_children
