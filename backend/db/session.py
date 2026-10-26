"""Engine / Session。同时服务 FastAPI 与 Celery worker（同步 SQLAlchemy 2.0）。"""
from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..config import get_settings

settings = get_settings()


def _build_engine():
    url = settings.database_url
    kwargs = {"future": True, "pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db() -> None:
    """开发便捷：直接建表。生产请使用 alembic。"""
    from app.db.base import Base
    from app.db import register_models

    register_models()
    Base.metadata.create_all(engine)


@contextmanager
def session_scope():
    """事务性 session 上下文：正常提交，异常回滚后重抛。"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db():
    """FastAPI 依赖：请求级 session，由请求生命周期结束（未 commit 自动回滚）。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()