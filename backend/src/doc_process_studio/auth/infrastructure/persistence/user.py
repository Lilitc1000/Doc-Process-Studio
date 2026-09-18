from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ....common.infrastructure.database import Base
from ...domain.roles import ROLE_MEMBER


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_color: Mapped[str] = mapped_column(String(7), default="#4f46e5", nullable=False)
    # 全局角色（admin / member），决定能否修改全系统共享的设置（如 RAGFlow 凭据）。
    # 注意：事故报告模块的角色在 incident_report_user_roles 表，与本列无关。
    role: Mapped[str] = mapped_column(String(20), default=ROLE_MEMBER, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
