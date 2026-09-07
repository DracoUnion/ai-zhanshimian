"""订单表（解锁包 + 充值共用）。"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutil import utcnow
from app.db.base import Base


class OrderType(str, Enum):
    unlock = "unlock"
    recharge = "recharge"


class OrderStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    closed = "closed"
    refunded = "refunded"


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_orders_amount"),
        CheckConstraint("order_type IN ('unlock','recharge')", name="chk_orders_type"),
        CheckConstraint("status IN ('pending','paid','closed','refunded')", name="chk_orders_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), default=OrderType.recharge.value, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)          # 分
    credits: Mapped[int] = mapped_column(Integer, nullable=False)         # 本单到账次数（快照）
    status: Mapped[str] = mapped_column(String(16), default=OrderStatus.pending.value, server_default="pending", nullable=False)
    pay_method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    prepay_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    out_trade_no: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    notify_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)