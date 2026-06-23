import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ...core.database import Base


def _generate_uuid() -> str:
    return uuid.uuid4().hex


class KBProject(Base):
    __tablename__ = "kb_projects"
    __table_args__ = (Index("idx_kb_projects_name", "name", unique=True),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    folder_count: Mapped[int] = mapped_column(Integer, default=0)
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    is_updating: Mapped[bool] = mapped_column(Boolean, default=False)
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class KBFolder(Base):
    __tablename__ = "kb_folders"
    __table_args__ = (
        Index("idx_kb_folders_project_id", "project_id"),
        Index("idx_kb_folders_parent_id", "parent_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("kb_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("kb_folders.id", ondelete="CASCADE"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class KBDocument(Base):
    __tablename__ = "kb_documents"
    __table_args__ = (
        Index("idx_kb_documents_project_id", "project_id"),
        Index("idx_kb_documents_folder_id", "folder_id"),
        Index("idx_kb_documents_content_hash", "content_hash"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("kb_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    folder_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("kb_folders.id", ondelete="SET NULL"),
        nullable=True,
    )
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
