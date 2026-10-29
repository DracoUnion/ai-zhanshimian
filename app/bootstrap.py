"""应用引导：装配 AppContext，确保数据目录、建表、种子模板、本机账户、后台线程池就绪。"""
from __future__ import annotations

import logging

from config import get_settings
from db.session import init_db
from scripts.seed_templates import seed_templates
from services.local_user import ensure_local_user
from tasks.generation_exec import configure_pool
from common.context import AppContext
from common.events import EventHub
from tasks.task import TaskManager

logger = logging.getLogger(__name__)
settings = get_settings()


def bootstrap() -> AppContext:
    """桌面端启动前调用一次（幂等）。返回装配好的 :class:`AppContext`。

    调用方应为 `main()`；测试可注入临时 settings mock 后复用。
    """
    settings.ensure_dirs()
    if settings.auto_create_tables:
        init_db()
        logger.info("数据库表已就绪")
    if settings.seed_demo_templates:
        seed_templates()
    ensure_local_user()
    configure_pool(settings.generation_workers)
    logger.info("本机账户与生图线程池已就绪")

    ctx = build_context()
    return ctx


def build_context() -> AppContext:
    """零 Qt 侧装配：EventHub + 通用 TaskManager → AppContext。"""
    events = EventHub()
    tasks = TaskManager(max_workers=max(1, settings.generation_workers), events=events)
    return AppContext(
        settings=settings,
        events=events,
        tasks=tasks,
    )