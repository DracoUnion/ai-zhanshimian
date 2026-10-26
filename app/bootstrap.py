"""应用引导：确保数据目录、建表、种子模板、本机账户、后台线程池就绪。"""
from __future__ import annotations

import logging

from config import get_settings
from db.session import init_db
from scripts.seed_templates import seed_templates
from services.local_user import ensure_local_user
from tasks.generation_exec import configure_pool

logger = logging.getLogger(__name__)
settings = get_settings()


def bootstrap() -> None:
    """桌面端启动前调用一次（幂等）。"""
    settings.ensure_dirs()
    if settings.auto_create_tables:
        init_db()
        logger.info("数据库表已就绪")
    if settings.seed_demo_templates:
        seed_templates()
    ensure_local_user()
    configure_pool(settings.generation_workers)
    logger.info("本机账户与生图线程池已就绪")