from sqlalchemy import Column, DateTime, ForeignKey, PrimaryKeyConstraint, String
from sqlalchemy.orm import relationship

from ...core.database import Base
from ...shared.dtutils import utcnow


class IncidentReportRole(Base):
    __tablename__ = "incident_report_roles"

    user_id = Column(String(32), ForeignKey("users.user_id"), nullable=False)
    role = Column(String(20), nullable=False)
    assigned_by = Column(String(32), ForeignKey("users.user_id"), nullable=True)
    assigned_at = Column(DateTime, default=utcnow)

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "role"),
    )
