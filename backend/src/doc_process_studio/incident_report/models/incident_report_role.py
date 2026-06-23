from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, PrimaryKeyConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...core.database import Base
from ...shared.dtutils import utcnow


class IncidentReportRoleDefinition(Base):
    __tablename__ = "incident_report_role_definitions"

    role_key: Mapped[str] = mapped_column(String(20), primary_key=True)
    role_name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user_roles: Mapped[list["IncidentReportUserRole"]] = relationship(back_populates="role_definition")
    role_permissions: Mapped[list["IncidentReportRolePermission"]] = relationship(back_populates="role_definition")


class IncidentReportUserRole(Base):
    __tablename__ = "incident_report_user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_key", name="uq_user_role"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.user_id"), nullable=False)
    role_key: Mapped[str] = mapped_column(
        String(20), ForeignKey("incident_report_role_definitions.role_key"), nullable=False
    )
    assigned_by: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.user_id"), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    role_definition: Mapped["IncidentReportRoleDefinition"] = relationship(back_populates="user_roles")


class IncidentReportPermission(Base):
    __tablename__ = "incident_report_permissions"

    permission_key: Mapped[str] = mapped_column(String(50), primary_key=True)
    permission_name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False)

    role_permissions: Mapped[list["IncidentReportRolePermission"]] = relationship(back_populates="permission")


class IncidentReportRolePermission(Base):
    __tablename__ = "incident_report_role_permissions"
    __table_args__ = (PrimaryKeyConstraint("role_key", "permission_key"),)

    role_key: Mapped[str] = mapped_column(
        String(20), ForeignKey("incident_report_role_definitions.role_key"), nullable=False
    )
    permission_key: Mapped[str] = mapped_column(
        String(50), ForeignKey("incident_report_permissions.permission_key"), nullable=False
    )

    role_definition: Mapped["IncidentReportRoleDefinition"] = relationship(back_populates="role_permissions")
    permission: Mapped["IncidentReportPermission"] = relationship(back_populates="role_permissions")
