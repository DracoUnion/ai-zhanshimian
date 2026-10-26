"""生成受理（含并发/幂等，对应详细设计 5.1）与结果组装。"""
from __future__ import annotations

from sqlalchemy import select, update, false, true
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import BizError, ErrCode
from app.models.generation import Generation
from app.models.idempotency import IdempotencyKey
from app.models.template import Template
from app.models.user import User
from app.schemas.generation import GenerationCreate
from app.services.billing import lock_user, record_balance
from app.services.storage import get_storage

settings = get_settings()


def accept_generation(db: Session, user: User, req: GenerationCreate, idem_key: str | None) -> Generation:
    """创建生成记录、执行试算/扣费、投递异步任务。

    - Idempotency-Key 防前端双击重复扣费；
    - 行锁 + 原子 UPDATE 保证并发安全；
    - 免费试用：trial_used 原子抢占，不落账本；
    - 付费：余额不足/未解锁直接拒。
    """
    # --- 幂等：已处理的 key 直接返回原记录 ---
    if idem_key:
        existing = db.scalar(select(IdempotencyKey).where(IdempotencyKey.key == idem_key))
        if existing:
            if existing.ref_type != "generation" or existing.user_id != user.id:
                raise BizError(ErrCode.FORBIDDEN, "重复请求", status_code=400)
            gen = db.get(Generation, existing.ref_id)
            if gen:
                return gen
            raise BizError(ErrCode.GENERATION_NOT_FOUND, "原生成记录已被清理")

    user = lock_user(db, user.id)
    if user.status != 0:
        raise BizError(ErrCode.FORBIDDEN, "账号不可用", status_code=403)

    trial = False
    credit_cost = 0
    charged = False

    if not user.trial_used:
        res = db.execute(
            update(User)
            .where(User.id == user.id, User.trial_used == false())
            .values(trial_used=true())
        )
        trial = res.rowcount == 1

    if not trial:
        if not user.unlocked:
            raise BizError(ErrCode.FEATURE_LOCKED, "尚未解锁，请先购买 69 元解锁包")
        if user.credits < req.quantity:
            raise BizError(ErrCode.BALANCE_INSUFFICIENT, "生成次数不足，请充值")
        user.credits -= req.quantity
        credit_cost = req.quantity
        charged = True

    gen = Generation(
        user_id=user.id,
        selfie_key=req.selfie_key,
        reference_key=req.reference_key or None,
        prompt=req.prompt,
        template_id=req.template_id,
        quantity=req.quantity,
        status="pending",
        credit_cost=credit_cost,
        charged=charged,
    )
    db.add(gen)
    db.flush()

    if charged:
        record_balance(
            db,
            user.id,
            -credit_cost,
            "consume",
            balance_after=user.credits,
            ref_id=gen.id,
            remark="生成扣费",
        )

    if idem_key:
        db.add(IdempotencyKey(key=idem_key, user_id=user.id, ref_type="generation", ref_id=gen.id))

    db.commit()

    # 投递异步任务（开发 eager 模式内联执行；生产走 Celery worker）
    from app.tasks.generation_tasks import run_generation_task

    run_generation_task.delay(gen.id)

    db.refresh(gen)
    return gen


def build_generation_detail(db: Session, gen: Generation) -> dict:
    store = get_storage()
    template = None
    if gen.template_id:
        t = db.get(Template, gen.template_id)
        if t:
            template = {"id": t.id, "name": t.name, "cover_url": store.sign_view(t.cover_key) if t.cover_key else None}

    results = []
    for key in gen.result_keys or []:
        results.append({"url": store.sign_view(key, settings.view_sign_ttl), "width": 0, "height": 0})

    return {
        "generation_id": gen.id,
        "status": gen.status,
        "quantity": gen.quantity,
        "credit_cost": gen.credit_cost,
        "charged": gen.charged,
        "selfie_url": store.sign_view(gen.selfie_key, settings.view_sign_ttl),
        "reference_url": store.sign_view(gen.reference_key, settings.view_sign_ttl) if gen.reference_key else None,
        "prompt": gen.prompt,
        "template": template,
        "results": results,
        "fail_reason": gen.fail_reason,
        "created_at": gen.created_at,
        "finished_at": gen.finished_at,
    }


def build_generation_list_item(db: Session, gen: Generation) -> dict:
    store = get_storage()
    template_name = None
    if gen.template_id:
        t = db.get(Template, gen.template_id)
        template_name = t.name if t else None
    keys = gen.result_keys or []
    return {
        "generation_id": gen.id,
        "status": gen.status,
        "quantity": gen.quantity,
        "credit_cost": gen.credit_cost,
        "template_name": template_name,
        "first_result_url": store.sign_view(keys[0], settings.view_sign_ttl) if keys else None,
        "created_at": gen.created_at,
    }