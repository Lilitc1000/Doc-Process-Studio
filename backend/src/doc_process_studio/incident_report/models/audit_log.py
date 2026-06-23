from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ...core.database import Base


class IncidentAuditLog(Base):
    __tablename__ = "incident_audit_logs"
    __table_args__ = (Index("idx_incident_audit_logs_report_id", "report_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    report_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("incident_reports.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.user_id"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
