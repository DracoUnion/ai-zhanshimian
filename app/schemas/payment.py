"""支付/计费相关 Schema。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RechargeReq(BaseModel):
    amount: int = Field(gt=0)
    order_type: Literal["recharge", "unlock"] = "recharge"
    pay_type: Literal["h5", "native"] = "h5"


class CreatePaymentOut(BaseModel):
    order_no: str
    status: str
    pay_params: dict


class MockConfirmReq(BaseModel):
    order_no: str
    out_trade_no: str | None = None
    paid_amount: int | None = None


class OrderOut(BaseModel):
    order_no: str
    order_type: str
    status: str
    amount: int
    credits: int
    created_at: datetime | None = None
    paid_at: datetime | None = None