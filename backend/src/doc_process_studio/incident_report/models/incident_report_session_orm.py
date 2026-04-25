from sqlalchemy import Column, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB

from ...core.database import Base


class IncidentReportSession(Base):
    __tablename__ = "incident_report_sessions"
    __table_args__ = (
        Index("idx_incident_report_sessions_updated_at", "updated_at"),
    )

    id = Column(String(64), primary_key=True)
    title = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    snapshot = Column(JSONB, nullable=True)
