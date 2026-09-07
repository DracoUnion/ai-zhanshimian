"""生成任务（对应详细设计 5.3 状态机）。

  pending --→ processing --→ success（已扣费）
                         └──→ failed → refund（退回费用）

失败采用任务内重试（退避），重试耗尽才置 failed 并退款；
另提供 sweep 任务兜底：worker 崩溃挂起的 pending/processing 超 5 分钟自动失败退款。
"""
from __future__ import annotations

import time
import uuid
from datetime import timedelta

from sqlalchemy import select

from app.core.timeutil import coerce_aware, utcnow
from app.db.session import SessionLocal
from app.models.generation import Generation
from app.models.template import Template
from app.services.aigc import get_aigc
from app.services.billing import refund_generation
from app.services.storage import get_storage
from app.tasks.celery_app import celery_app

MAX_RETRIES = 3
STUCK_MINUTES = 5


@celery_app.task(name="run_generation", ignore_result=True)
def run_generation_task(gen_id: int) -> None:
    _execute_generation(gen_id)


def _execute_generation(gen_id: int) -> None:
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
    with SessionLocal() as db:
        gen = db.get(Generation, gen_id)
        if gen is None:
            return
        gen.status = "failed"
        gen.fail_reason = reason[:200]
        gen.finished_at = utcnow()
        refund_generation(db, gen)
        db.commit()


@celery_app.task(name="sweep_stuck_generations", ignore_result=True)
def sweep_stuck_generations() -> None:
    """兜底：超时未完成的生成任务 → 失败 + 退款（防 worker 崩溃挂起）。"""
    now = utcnow()
    with SessionLocal() as db:
        cutoff = now - timedelta(minutes=STUCK_MINUTES)
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
                gen.fail_reason = "处理超时，已自动退回次数"
                gen.finished_at = utcnow()
                refund_generation(db, gen)
        db.commit()