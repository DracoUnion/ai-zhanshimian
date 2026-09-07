"""余额流水（唯一审计账本）。"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import utcnow
from app.db.base import Base


class BalanceTxType(str, Enum):
    recharge = "recharge"
    consume = "consume"
    refund = "refund"
    gift = "gift"
    unlock = "unlock"


class BalanceTransaction(Base):
    __tablename__ = "balance_transactions"
    __table_args__ = (
        CheckConstraint("amount <> 0", name="chk_bt_amount"),
        CheckConstraint("type IN ('recharge','consume','refund','gift','unlock')", name="chk_bt_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)         # 正=增 负=扣
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)  # 变动后余额快照
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)