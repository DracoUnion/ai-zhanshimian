"""模板相关 Schema。"""
from __future__ import annotations

from pydantic import BaseModel


class TemplateOut(BaseModel):
    id: int
    name: str
    category: str
    cover_url: str | None = None
    prompt_template: str
    prompt_tips: str | None = None
    sort: int = 0


class TemplateListOut(BaseModel):
    items: list[TemplateOut]