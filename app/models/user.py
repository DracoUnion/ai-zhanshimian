"""本机账户表（单机模式，无登录）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.timeutil import utcnow
from db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(32), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now(), nullable=False
    )