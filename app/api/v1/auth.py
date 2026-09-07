"""认证：短信验证码登录 + Token 刷新。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.cache import get_kv
from app.core.errors import BizError, ErrCode
from app.core.response import ok
from app.core.security import create_access_token, create_refresh_token, decode_token, generate_sms_code, safe_equals
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import PhoneLoginReq, RefreshReq, RefreshOut, SmsCodeOut, SmsCodeReq, TokenOut
from app.schemas.user import UserOut
from app.services.sms import get_sms

router = APIRouter()
settings = get_settings()


@router.post("/sms-code")
def send_sms_code(req: SmsCodeReq) -> dict:
    kv = get_kv()
    if kv.get(f"sms_cooldown:{req.phone}"):
        raise BizError(ErrCode.SMS_TOO_FREQUENT, "发送过于频繁，请稍后再试")
    code = generate_sms_code()

    def _send_and_mark():
        kv.set(f"sms:{req.phone}", code, ttl=settings.sms_code_ttl)
        kv.set(f"sms_cooldown:{req.phone}", "1", ttl=settings.sms_cooldown)
        get_sms().send(req.phone, code)

    _send_and_mark()
    return ok(SmsCodeOut(cooldown=settings.sms_cooldown).model_dump())


@router.post("/phone-login")
def phone_login(req: PhoneLoginReq, db: Session = Depends(get_db)) -> dict:
    kv = get_kv()
    saved = kv.get(f"sms:{req.phone}")
    if not saved or not safe_equals(saved, req.code):
        raise BizError(ErrCode.SMS_CODE_INVALID, "验证码错误或已过期")
    kv.delete(f"sms:{req.phone}")

    user = db.scalar(select(User).where(User.phone == req.phone))
    if user is None:
        user = User(phone=req.phone)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif user.status != 0:
        raise BizError(ErrCode.FORBIDDEN, "账号不可用", status_code=403)

    data = TokenOut(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.access_token_ttl,
        user=UserOut.model_validate(user),
    ).model_dump()
    return ok(data)


@router.post("/refresh")
def refresh(req: RefreshReq) -> dict:
    user_id = decode_token(req.refresh_token, "refresh")
    return ok(RefreshOut(access_token=create_access_token(user_id), expires_in=settings.access_token_ttl).model_dump())


@router.post("/dev-code")
def dev_code(req: SmsCodeReq) -> dict:
    """仅开发/sms mock 联调：读取发给该手机号的验证码。"""
    if settings.env != "dev" and settings.sms_provider != "mock":
        raise BizError(ErrCode.FORBIDDEN, "仅开发模式可用", status_code=403)
    code = get_kv().get(f"dev_sms:{req.phone}")
    return ok({"phone": req.phone, "code": code})