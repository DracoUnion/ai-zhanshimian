"""认证相关 Schema。"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.user import UserOut

PHONE_PATTERN = r"^1[3-9]\d{9}$"


class SmsCodeReq(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN)


class SmsCodeOut(BaseModel):
    cooldown: int


class PhoneLoginReq(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN)
    code: str = Field(min_length=4, max_length=8)


class RefreshReq(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user: UserOut


class RefreshOut(BaseModel):
    access_token: str
    expires_in: int