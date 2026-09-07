"""时间工具。"""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def coerce_aware(dt: datetime) -> datetime:
    """SQLite 返回 naive datetime，统一补时区，保证 Python 侧比较安全。"""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)