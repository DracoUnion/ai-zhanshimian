"""生成：创建（幂等+并发安全）、详情、历史、删除。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import BizError, ErrCode
from app.core.response import ok
from app.core.timeutil import utcnow
from app.db.session import get_db
from app.models.generation import Generation
from app.models.user import User
from app.schemas.generation import (
    GenerationCreate,
    GenerationCreateOut,
    GenerationDetail,
    GenerationListOut,
    GenerationListItem,
)
from app.services.generation import accept_generation, build_generation_detail, build_generation_list_item

router = APIRouter()


@router.post("")
def create_generation(
    req: GenerationCreate,
    idem_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    # 防越权：只允许使用自己命名空间上传的对象（u/{user_id}/...）
    if not req.selfie_key.startswith(f"u/{user.id}/"):
        raise BizError(ErrCode.UPLOAD_INVALID, "图片来源非法")
    if req.reference_key and not req.reference_key.startswith(f"u/{user.id}/"):
        raise BizError(ErrCode.UPLOAD_INVALID, "参考图来源非法")

    gen = accept_generation(db, user, req, idem_key)
    fresh = db.get(User, user.id)
    return ok(
        GenerationCreateOut(
            generation_id=gen.id,
            status=gen.status,
            quantity=gen.quantity,
            credit_cost=gen.credit_cost,
            trial_used=fresh.trial_used if fresh else user.trial_used,
            balance=fresh.credits if fresh else user.credits,
        ).model_dump()
    )


def _owned_generation(db: Session, user_id: int, gen_id: int) -> Generation:
    gen = db.scalar(
        select(Generation).where(Generation.id == gen_id, Generation.user_id == user_id, Generation.deleted_at.is_(None))
    )
    if gen is None:
        raise BizError(ErrCode.GENERATION_NOT_FOUND, "生成记录不存在", status_code=404)
    return gen


@router.get("/{gen_id}")
def generation_detail(gen_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    gen = _owned_generation(db, user.id, gen_id)
    return ok(GenerationDetail(**build_generation_detail(db, gen)).model_dump())


@router.get("")
def generation_list(
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    page = max(1, page)
    page_size = max(1, min(page_size, 50))
    total = db.scalar(
        select(func.count()).select_from(Generation).where(Generation.user_id == user.id, Generation.deleted_at.is_(None))
    )
    rows = db.execute(
        select(Generation)
        .where(Generation.user_id == user.id, Generation.deleted_at.is_(None))
        .order_by(Generation.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    items = [GenerationListItem(**build_generation_list_item(db, g)) for g in rows]
    return ok(
        GenerationListOut(
            items=items, total=total or 0, page=page, page_size=page_size, has_more=(page * page_size) < (total or 0)
        ).model_dump()
    )


@router.delete("/{gen_id}")
def delete_generation(gen_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    gen = _owned_generation(db, user.id, gen_id)
    gen.deleted_at = utcnow()
    db.commit()
    return ok(None)