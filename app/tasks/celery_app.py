"""Celery 应用。

- 开发/默认：CELERY_EAGER=true 任务内联执行（无需 broker）。
- 生产：CELERY_EAGER=false + CELERY_BROKER_URL=redis://... 独立 worker 进程：
      celery -A app.tasks.celery_app.celery_app worker -l info
"""
from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "zhanshi",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_always_eager=settings.celery_eager,
    task_eager_propagates=True,
    task_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_prefetch_multiplier=1,
)