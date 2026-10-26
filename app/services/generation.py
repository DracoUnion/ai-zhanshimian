"""生成受理（幂等，防前端双击重复提交）与结果组装。免费无限次，无扣费。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import BizError, ErrCode
from app.models.generation import Generation
from app.models.idempotency import IdempotencyKey
from app.models.template import Template
from app.models.user import User
from app.schemas.generation import GenerationCreate
from app.services.storage import get_storage

settings = get_settings()


def accept_generation(db: Session, user: User, req: GenerationCreate, idem_key: str | None) -> Generation:
    """创建生成记录并投递后台任务。免费无限次；Idempotency-Key 防重复提交。"""
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

    gen = Generation(
        user_id=user.id,
        selfie_key=req.selfie_key,
        reference_key=req.reference_key or None,
        prompt=req.prompt,
        template_id=req.template_id,
        quantity=req.quantity,
        status="pending",
    )
    db.add(gen)
    db.flush()

    if idem_key:
        db.add(IdempotencyKey(key=idem_key, user_id=user.id, ref_type="generation", ref_id=gen.id))

    db.commit()

    # 投递后台任务（桌面端线程池内联执行；见 app/tasks/generation_exec.py）
    from app.tasks.generation_exec import submit_generation

    submit_generation(gen.id)

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
        "template_name": template_name,
        "first_result_url": store.sign_view(keys[0], settings.view_sign_ttl) if keys else None,
        "created_at": gen.created_at,
    }