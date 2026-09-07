"""后台管理端点（X-Admin-Key 保护）：老用户权益补发 / 运营发放。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.errors import BizError, ErrCode
from app.core.response import ok
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import GrantCreditsOut, GrantCreditsReq
from app.schemas.user import UserOut
from app.services.billing import add_balance

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/users/search")
def search_user(phone: str, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.phone == phone))
    return ok({"items": [UserOut.model_validate(user).model_dump()] if user else []})


@router.post("/users/{user_id}/credits")
def grant_credits(user_id: int, req: GrantCreditsReq, db: Session = Depends(get_db)) -> dict:
    user = db.get(User, user_id)
    if user is None:
        raise BizError(ErrCode.FORBIDDEN, "用户不存在", status_code=404)
    user = add_balance(db, user_id, req.credits, "gift", remark=req.remark or "运营发放")
    db.commit()
    db.refresh(user)
    return ok(GrantCreditsOut(user_id=user.id, credits_added=req.credits, balance=user.credits).model_dump())