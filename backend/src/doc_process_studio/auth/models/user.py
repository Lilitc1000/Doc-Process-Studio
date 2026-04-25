from sqlalchemy import Column, DateTime, Integer, String, func

from ...core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(32), unique=True, nullable=False, index=True)
    username = Column(String(20), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    avatar_color = Column(String(7), default="#4f46e5", nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
