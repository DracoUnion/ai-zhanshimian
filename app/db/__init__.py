"""数据库层。"""
from __future__ import annotations


def register_models() -> None:
    """导入所有模型模块，确保 Base.metadata 完整（建表/迁移用）。"""
    from app import models  # noqa: F401

    _ = models