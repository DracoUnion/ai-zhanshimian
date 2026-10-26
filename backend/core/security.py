"""JWT 签发/校验 + 短信验证码生成。"""
from __future__ import annotations

import hmac
import random
from typing import Literal

import jwt

from ..config import get_settings
from .errors import BizError, ErrCode

settings = get_settings()

TokenType = Literal["access", "refresh"]


def create_access_token(user_id: int) -> str:
    return _encode(user_id, "access", settings.access_token_ttl)


def create_refresh_token(user_id: int) -> str:
    return _encode(user_id, "refresh", settings.refresh_token_ttl)


def _encode(user_id: int, token_type: TokenType, ttl: int) -> str:
    now = int(__import__("time").time())
    payload = {"sub": str(user_id), "type": token_type, "iat": now, "exp": now + ttl}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str, expected_type: TokenType) -> int:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise BizError(ErrCode.TOKEN_EXPIRED, "登录已过期，请重新登录", status_code=401)
    except jwt.InvalidTokenError:
        raise BizError(ErrCode.UNAUTHORIZED, "无效凭证", status_code=401)
    if payload.get("type") != expected_type:
        raise BizError(ErrCode.UNAUTHORIZED, "凭证类型错误", status_code=401)
    try:
        return int(payload["sub"])
    except (KeyError, ValueError):
        raise BizError(ErrCode.UNAUTHORIZED, "无效凭证", status_code=401)


def generate_sms_code() -> str:
    return f"{random.randint(0, 999999):06d}"


def safe_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())