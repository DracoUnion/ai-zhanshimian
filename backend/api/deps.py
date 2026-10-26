"""FastAPI 依赖：当前用户、后台凭证、DB session。"""
from __future__ import annotations

import hmac

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import BizError, ErrCode
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

settings = get_settings()
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise BizError(ErrCode.UNAUTHORIZED, "请先登录", status_code=401)
    user_id = decode_token(credentials.credentials, "access")
    user = db.get(User, user_id)
    if user is None or user.status != 0:
        raise BizError(ErrCode.FORBIDDEN, "账号不可用", status_code=403)
    return user


def require_admin(x_admin_key: str = Header(default=None, alias="X-Admin-Key")) -> None:
    if not x_admin_key or not hmac.compare_digest(x_admin_key, settings.admin_key):
        raise BizError(ErrCode.FORBIDDEN, "后台凭证无效", status_code=403)