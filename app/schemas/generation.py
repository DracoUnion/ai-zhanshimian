"""生成相关 Schema。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class GenerationCreate(BaseModel):
    selfie_key: str = Field(min_length=1, max_length=512)
    reference_key: str | None = Field(default=None, max_length=512)
    template_id: int | None = None
    prompt: str | None = Field(default=None, max_length=500)
    quantity: int = Field(default=1, ge=1, le=12)

    @model_validator(mode="after")
    def _check_source(self):
        if self.template_id is None and not (self.prompt and self.prompt.strip()):
            raise ValueError("template_id 与 prompt 至少提供其一")
        return self


class GenerationCreateOut(BaseModel):
    generation_id: int
    status: str
    quantity: int
    credit_cost: int
    trial_used: bool
    balance: int


class TemplateBrief(BaseModel):
    id: int
    name: str
    cover_url: str | None = None


class ResultImage(BaseModel):
    url: str
    width: int = 0
    height: int = 0


class GenerationDetail(BaseModel):
    generation_id: int
    status: str
    quantity: int
    credit_cost: int
    charged: bool
    selfie_url: str | None = None
    reference_url: str | None = None
    prompt: str | None = None
    template: TemplateBrief | None = None
    results: list[ResultImage] = []
    fail_reason: str | None = None
    created_at: datetime | None = None
    finished_at: datetime | None = None


class GenerationListItem(BaseModel):
    generation_id: int
    status: str
    quantity: int
    credit_cost: int
    template_name: str | None = None
    first_result_url: str | None = None
    created_at: datetime | None = None


class GenerationListOut(BaseModel):
    items: list[GenerationListItem]
    total: int
    page: int
    page_size: int
    has_more: bool