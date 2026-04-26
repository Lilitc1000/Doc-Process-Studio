from sqlalchemy import Column, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB

from ...core.database import Base


class IncidentReport(Base):
    __tablename__ = "incident_reports"
    __table_args__ = (
        Index("idx_incident_reports_status", "status"),
        Index("idx_incident_reports_reporter_id", "reporter_id"),
        Index("idx_incident_reports_updated_at", "updated_at"),
    )

    id = Column(String(32), primary_key=True)
    ref_no = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    severity = Column(String(10), nullable=True)

    reporter_id = Column(String(32), ForeignKey("users.user_id"), nullable=False)
    assignee_id = Column(String(32), ForeignKey("users.user_id"), nullable=True)
    verifier_id = Column(String(32), ForeignKey("users.user_id"), nullable=True)

    system = Column(String(100), nullable=True)
    site_id = Column(String(100), nullable=True)
    fault_date = Column(DateTime(timezone=True), nullable=True)
    resolution_date = Column(DateTime(timezone=True), nullable=True)

    form_data = Column(JSONB, default=dict)
    report_data = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)


class IncidentComment(Base):
    __tablename__ = "incident_comments"
    __table_args__ = (
        Index("idx_incident_comments_report_id", "report_id"),
    )

    id = Column(String(32), primary_key=True)
    report_id = Column(String(32), ForeignKey("incident_reports.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(String(32), ForeignKey("users.user_id"), nullable=False)
    content = Column(String, nullable=False)
    parent_id = Column(String(32), ForeignKey("incident_comments.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
