"""应用门面：UI 直接调用的服务入口（无 HTTP 层）。

每个操作自开会话，返回纯数据（dict / Pydantic schema），UI 不感知 ORM/session。
单机模式：所有操作作用于「本机账户」（见 services/local_user.py）。
"""
from __future__ import annotations

from sqlalchemy import func, select

from app.config import get_settings
from app.core.errors import BizError, ErrCode
from app.core.timeutil import utcnow
from app.db.session import session_scope
from app.models.generation import Generation
from app.models.user import User
from app.schemas.generation import (
    GenerationCreate,
    GenerationDetail,
    GenerationListOut,
    GenerationListItem,
)
from app.schemas.template import TemplateOut
from app.schemas.user import UserOut
from app.services import generation as generation_service
from app.services.local_user import get_local_user
from app.services.storage import get_storage
from app.services.upload import upload_service

settings = get_settings()


# ---------- 本机账户 ----------
def state() -> dict:
    """本机账户信息（免费无限次，无余额/解锁概念）。"""
    with session_scope() as db:
        user = get_local_user(db)
        return {
            "user_id": user.id,
            "nickname": user.nickname,
        }


def update_profile(*, nickname: str | None = None) -> dict:
    with session_scope() as db:
        user = get_local_user(db)
        if nickname is not None:
            user.nickname = nickname.strip()[:32] or None
        db.refresh(user)
        return UserOut.model_validate(user).model_dump()


# ---------- 模板 ----------
def templates() -> list[dict]:
    with session_scope() as db:
        from app.models.template import Template
        from sqlalchemy import select

        rows = db.execute(
            select(Template).where(Template.enabled == True).order_by(Template.sort.asc(), Template.id.asc())  # noqa: E712
        ).scalars().all()
        store = get_storage()
        items = [
            TemplateOut(
                id=t.id,
                name=t.name,
                category=t.category,
                cover_url=store.sign_view(t.cover_key, settings.view_sign_ttl) if t.cover_key else None,
                prompt_template=t.prompt_template,
                prompt_tips=t.prompt_tips,
                sort=t.sort,
            )
            for t in rows
        ]
        return [TemplateOut.model_validate(i).model_dump() for i in items]


# ---------- 上传 ----------
def upload_image(kind: str, data: bytes, content_type: str) -> dict:
    with session_scope() as db:
        user = get_local_user(db)
        user_id = user.id
    return upload_service.save_image(user_id, kind, data, content_type)


# ---------- 生成 ----------
def create_generation(
    *,
    selfie_key: str,
    reference_key: str | None = None,
    template_id: int | None = None,
    prompt: str | None = None,
    quantity: int = 1,
    idempotency_key: str | None = None,
) -> dict:
    req = GenerationCreate(
        selfie_key=selfie_key,
        reference_key=reference_key or None,
        template_id=template_id,
        prompt=(prompt or "").strip() or None,
        quantity=quantity,
    )
    with session_scope() as db:
        user = get_local_user(db)
        # 防越权：只允许本机账户命名空间的对象
        if not req.selfie_key.startswith(f"u/{user.id}/"):
            raise BizError(ErrCode.UPLOAD_INVALID, "图片来源非法")
        if req.reference_key and not req.reference_key.startswith(f"u/{user.id}/"):
            raise BizError(ErrCode.UPLOAD_INVALID, "参考图来源非法")

        gen = generation_service.accept_generation(db, user, req, idempotency_key)
        return {
            "generation_id": gen.id,
            "status": gen.status,
            "quantity": gen.quantity,
        }


def generation_detail(gen_id: int) -> dict:
    with session_scope() as db:
        user = get_local_user(db)
        gen = db.scalar(
            select(Generation).where(
                Generation.id == gen_id, Generation.user_id == user.id, Generation.deleted_at.is_(None)
            )
        )
        if gen is None:
            raise BizError(ErrCode.GENERATION_NOT_FOUND, "生成记录不存在", status_code=404)
        detail = generation_service.build_generation_detail(db, gen)
        return GenerationDetail(**detail).model_dump(mode="json")


def generation_list(page: int = 1, page_size: int = 20) -> dict:
    page = max(1, page)
    page_size = max(1, min(page_size, 50))
    with session_scope() as db:
        user = get_local_user(db)
        total = db.scalar(
            select(func.count()).select_from(Generation).where(Generation.user_id == user.id, Generation.deleted_at.is_(None))
        )
        rows = (
            db.execute(
                select(Generation)
                .where(Generation.user_id == user.id, Generation.deleted_at.is_(None))
                .order_by(Generation.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )
        items = [GenerationListItem(**generation_service.build_generation_list_item(db, g)) for g in rows]
        out = GenerationListOut(
            items=items, total=total or 0, page=page, page_size=page_size, has_more=(page * page_size) < (total or 0)
        )
        return out.model_dump(mode="json")


def delete_generation(gen_id: int) -> None:
    with session_scope() as db:
        user = get_local_user(db)
        gen = db.scalar(
            select(Generation).where(
                Generation.id == gen_id, Generation.user_id == user.id, Generation.deleted_at.is_(None)
            )
        )
        if gen is None:
            raise BizError(ErrCode.GENERATION_NOT_FOUND, "生成记录不存在", status_code=404)
        gen.deleted_at = utcnow()