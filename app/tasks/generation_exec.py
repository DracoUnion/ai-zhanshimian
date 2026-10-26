"""后台任务层：生图与卡单兜底（桌面端单进程替代原 Celery worker）。

- UI 线程只做受理（accept_generation），生图在 `ThreadPoolExecutor` 后台执行；
- 测试可置 `AUTO_RUN=False` 后手动同步调用 `run_generation(gen_id)` 获得确定性；
- 失败采用任务内重试（退避），重试耗尽才置 failed（免费无限次，无退款）；
  另有 `sweep_stuck_generations()` 兜底：挂起超时的 pending/processing 自动失败。
"""
from __future__ import annotations

import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from sqlalchemy import select

from core.timeutil import coerce_aware, utcnow
from db.session import SessionLocal
from models.generation import Generation
from models.template import Template
from services.aigc import get_aigc
from services.storage import get_storage

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
STUCK_MINUTES = 5

# 是否自动投递（默认 True）。测试设 False 以手动控制执行时机。
AUTO_RUN = True
_pool: ThreadPoolExecutor | None = None


def configure_pool(max_workers: int = 2) -> ThreadPoolExecutor | None:
    """启动时由应用入口调用：创建后台生图线程池。返回旧池（若有）。"""
    global _pool
    if _pool is not None:
        return _pool
    _pool = ThreadPoolExecutor(max_workers=max(1, max_workers), thread_name_prefix="zhanshi-gen")
    return _pool


def shutdown_pool(wait: bool = True) -> None:
    global _pool
    if _pool is not None:
        _pool.shutdown(wait=wait)
        _pool = None


def submit_generation(gen_id: int) -> None:
    """投递生图任务：优先后台线程池；无池且 AUTO_RUN 时同步内联（旧 eager 语义）。"""
    if _pool is not None:
        _pool.submit(run_generation, gen_id)
        return
    if AUTO_RUN:
        run_generation(gen_id)


def run_generation(gen_id: int) -> None:
    """执行一次生图：pending → processing → success / failed。"""
    with SessionLocal() as db:
        gen = db.get(Generation, gen_id)
        if gen is None or gen.status != "pending":
            return
        gen.status = "processing"
        db.commit()

        prompt = gen.prompt
        reference_bytes = None
        if gen.reference_key:
            reference_bytes = get_storage().open_bytes(gen.reference_key)
        if not prompt and gen.template_id:
            t = db.get(Template, gen.template_id)
            prompt = t.prompt_template if t else "优化人物展示面，突出氛围感"

        selfie_bytes = get_storage().open_bytes(gen.selfie_key)

    # 第三方生图（任务内重试，退避）
    aigc = get_aigc()
    outputs: list[bytes] = []
    attempt = 0
    while True:
        attempt += 1
        try:
            outputs = aigc.transform(selfie=selfie_bytes, prompt=prompt or "", reference=reference_bytes, n=gen.quantity)
            break
        except Exception as exc:  # noqa: BLE001
            logger.warning("生图第 %s 次尝试失败: %s", attempt, exc)
            if attempt >= MAX_RETRIES:
                _fail_and_refund(gen_id, f"生成失败: {exc}")
                return
            time.sleep(min(2 ** attempt, 30))

    # 落盘
    store = get_storage()
    keys: list[str] = []
    try:
        for blob in outputs:
            key = f"g/{gen.user_id}/{gen.id}/{uuid.uuid4().hex}.jpg"
            store.save_bytes(key, blob)
            keys.append(key)
    except Exception as exc:  # noqa: BLE001
        _fail_and_refund(gen_id, f"结果保存失败: {exc}")
        return

    with SessionLocal() as db:
        gen = db.get(Generation, gen_id)
        if gen is None:
            return
        gen.status = "success"
        gen.result_keys = keys
        gen.finished_at = utcnow()
        db.commit()


def _fail_and_refund(gen_id: int, reason: str) -> None:
    """生成失败置 failed（免费无限次，无退款）。"""
    with SessionLocal() as db:
        gen = db.get(Generation, gen_id)
        if gen is None:
            return
        gen.status = "failed"
        gen.fail_reason = reason[:200]
        gen.finished_at = utcnow()
        db.commit()


def sweep_stuck_generations() -> None:
    """兜底：超时未完成的生成任务 → 失败（免费无限次，无退款）。"""
    now = utcnow()
    cutoff = now - timedelta(minutes=STUCK_MINUTES)
    with SessionLocal() as db:
        rows = db.execute(
            select(Generation).where(
                Generation.status.in_(["pending", "processing"]),
                Generation.deleted_at.is_(None),
            )
        ).scalars().all()
        for gen in rows:
            created = coerce_aware(gen.created_at)
            if created < cutoff:
                gen.status = "failed"
                gen.fail_reason = "处理超时，已自动标记失败"
                gen.finished_at = utcnow()
                refund_generation(db, gen)
        db.commit()
