from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from ...core.database import Base


class IncidentAuditLog(Base):
    __tablename__ = "incident_audit_logs"
    __table_args__ = (
        Index("idx_incident_audit_logs_report_id", "report_id"),
    )

    id = Column(String(32), primary_key=True)
    report_id = Column(String(32), ForeignKey("incident_reports.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(20), nullable=False)
    actor_id = Column(String(32), ForeignKey("users.user_id"), nullable=False)
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=True)
    comment = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
