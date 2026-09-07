"""风格模板库（P1）。公开读取，落地页展示封面。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.response import ok
from app.db.session import get_db
from app.models.template import Template
from app.schemas.template import TemplateListOut, TemplateOut
from app.services.storage import get_storage

router = APIRouter()
settings = get_settings()


@router.get("")
def list_templates(db: Session = Depends(get_db)) -> dict:
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
    return ok(TemplateListOut(items=items).model_dump())