"""风格模板表。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import utcnow
from app.db.base import Base


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(32), default="life", server_default="life", nullable=False)
    cover_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_tips: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)