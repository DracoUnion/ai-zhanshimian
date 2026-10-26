"""生成记录表。"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, SmallInteger, String, Text, false, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import utcnow
from app.db.base import Base


class GenerationStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    success = "success"
    failed = "failed"


class Generation(Base):
    __tablename__ = "generations"
    __table_args__ = (
        CheckConstraint("quantity BETWEEN 1 AND 12", name="chk_gen_quantity"),
        CheckConstraint("status IN ('pending','processing','success','failed')", name="chk_gen_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    selfie_key: Mapped[str] = mapped_column(String(512), nullable=False)
    reference_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_id: Mapped[int | None] = mapped_column(ForeignKey("templates.id"), index=True, nullable=True)
    quantity: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=GenerationStatus.pending.value, server_default="pending", nullable=False)
    result_keys: Mapped[list | None] = mapped_column(JSON, nullable=True)
    credit_cost: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0", nullable=False)
    charged: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    fail_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)