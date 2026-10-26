"""后台管理 Schema。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class GrantCreditsReq(BaseModel):
    credits: int = Field(gt=0)
    remark: str | None = Field(default=None, max_length=255)


class GrantCreditsOut(BaseModel):
    user_id: int
    credits_added: int
    balance: int


class AdminUserSearchOut(BaseModel):
    items: list  # list[UserOut]