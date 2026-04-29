from sqlalchemy import Column, DateTime, ForeignKey, PrimaryKeyConstraint, String, UniqueConstraint
from sqlalchemy.orm import relationship

from ...core.database import Base
from ...shared.dtutils import utcnow


class IncidentReportRoleDefinition(Base):
    __tablename__ = "incident_report_role_definitions"

    role_key = Column(String(20), primary_key=True)
    role_name = Column(String(50), nullable=False)
    description = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user_roles = relationship("IncidentReportUserRole", back_populates="role_definition")
    role_permissions = relationship("IncidentReportRolePermission", back_populates="role_definition")


class IncidentReportUserRole(Base):
    __tablename__ = "incident_report_user_roles"

    id = Column(String(32), primary_key=True)
    user_id = Column(String(32), ForeignKey("users.user_id"), nullable=False)
    role_key = Column(String(20), ForeignKey("incident_report_role_definitions.role_key"), nullable=False)
    assigned_by = Column(String(32), ForeignKey("users.user_id"), nullable=True)
    assigned_at = Column(DateTime(timezone=True), default=utcnow)

    role_definition = relationship("IncidentReportRoleDefinition", back_populates="user_roles")

    __table_args__ = (
        UniqueConstraint("user_id", "role_key", name="uq_user_role"),
    )


class IncidentReportPermission(Base):
    __tablename__ = "incident_report_permissions"

    permission_key = Column(String(50), primary_key=True)
    permission_name = Column(String(50), nullable=False)
    description = Column(String(200), nullable=True)
    category = Column(String(20), nullable=False)

    role_permissions = relationship("IncidentReportRolePermission", back_populates="permission")


class IncidentReportRolePermission(Base):
    __tablename__ = "incident_report_role_permissions"

    role_key = Column(String(20), ForeignKey("incident_report_role_definitions.role_key"), nullable=False)
    permission_key = Column(String(50), ForeignKey("incident_report_permissions.permission_key"), nullable=False)

    role_definition = relationship("IncidentReportRoleDefinition", back_populates="role_permissions")
    permission = relationship("IncidentReportPermission", back_populates="role_permissions")

    __table_args__ = (
        PrimaryKeyConstraint("role_key", "permission_key"),
    )
