"""Engine / Session（同步 SQLAlchemy 2.0，桌面端单进程多线程使用）。

- SQLite 开启 WAL + busy_timeout，保证后台生图线程与 UI 线程读写并发不报
  "database is locked"；
- 业务操作一律通过 `session_scope()` 获得独立 session（正常提交、异常回滚）。
"""
from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from ..config import get_settings

settings = get_settings()


def _build_engine():
    url = settings.database_url
    kwargs = {"future": True, "pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        from sqlalchemy import text

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=10000")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    return engine


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
