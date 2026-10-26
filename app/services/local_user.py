"""本机账户（单机模式）。

无用户系统 / 无登录：应用自动维护一条 phone="local" 的本机账户，承载
免费试用、69 解锁、余额充值等全部计费状态。UI 不展示任何账户/注册信息。
"""
from __future__ import annotations

from sqlalchemy import select

from app.db.session import session_scope
from app.models.user import User


def get_local_user(db) -> User:
    """在已开启会话中取本机账户；不存在则创建（不提交由调用方管理）。"""
    user = db.scalar(select(User).where(User.phone == "local"))
    if user is None:
        user = User(phone="local")
        db.add(user)
        db.flush()
    return user


def ensure_local_user() -> User:
    """确保本机账户存在于库中并返回（自开会话）。"""
    with session_scope() as db:
        user = get_local_user(db)
        db.refresh(user)
        return user