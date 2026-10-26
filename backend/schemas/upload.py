"""上传相关 Schema。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PresignReq(BaseModel):
    kind: Literal["selfie", "reference"]
    content_type: str
    size: int = Field(ge=0, le=100 * 1024 * 1024)


class UploadTargetOut(BaseModel):
    object_key: str
    upload_url: str
    view_url: str
    expires_in: int
    method: str = "PUT"
    headers: dict[str, str] = {}


class SignViewReq(BaseModel):
    object_keys: list[str] = Field(default_factory=list, max_length=50)


class SignViewOut(BaseModel):
    urls: dict[str, str]