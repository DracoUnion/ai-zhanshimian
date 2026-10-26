"""ORM 模型（对应 doc/design-detail.md 第二章，去除支付/余额后的精简集）。"""
from __future__ import annotations

from models.generation import Generation, GenerationStatus
from models.idempotency import IdempotencyKey
from models.template import Template
from models.user import User

__all__ = [
    "User",
    "Generation",
    "GenerationStatus",
    "Template",
    "IdempotencyKey",
]