from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ...core.database import Base


class IncidentReport(Base):
    __tablename__ = "incident_reports"
    __table_args__ = (
        Index("idx_incident_reports_status", "status"),
        Index("idx_incident_reports_reporter_id", "reporter_id"),
        Index("idx_incident_reports_updated_at", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    ref_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    severity: Mapped[str | None] = mapped_column(String(10), nullable=True)

    reporter_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.user_id"), nullable=False)
    assignee_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.user_id"), nullable=True)
    verifier_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.user_id"), nullable=True)

    system: Mapped[str | None] = mapped_column(String(100), nullable=True)
    site_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fault_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    form_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    report_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IncidentComment(Base):
    __tablename__ = "incident_comments"
    __table_args__ = (
        Index("idx_incident_comments_report_id", "report_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    report_id: Mapped[str] = mapped_column(String(32), ForeignKey("incident_reports.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.user_id"), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("incident_comments.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
