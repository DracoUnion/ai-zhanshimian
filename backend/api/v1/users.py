"""用户信息 / 余额。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.response import ok
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserOut, UserUpdate

router = APIRouter()


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return ok(UserOut.model_validate(user).model_dump())


@router.patch("/me")
def update_user(req: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if req.nickname is not None:
        user.nickname = req.nickname.strip()[:32] or None
    if req.avatar_url is not None:
        user.avatar_url = req.avatar_url or None
    db.commit()
    db.refresh(user)
    return ok(UserOut.model_validate(user).model_dump())