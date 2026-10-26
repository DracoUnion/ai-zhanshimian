"""支付服务：下单入口 + 回调幂等结算（对应详细设计 5.2）。

- mock 模式：不调微信，配合 POST /payments/mock-confirm 模拟到账，用于开发/验收。
- wechat 模式：微信支付 v3 下单；回调验签 → AES 解密 → settle_paid_order（幂等）。
"""
from __future__ import annotations

import logging
import random
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import BizError, ErrCode
from app.models.balance import BalanceTransaction
from app.models.order import Order
from app.models.user import User
from app.services.billing import lock_user

logger = logging.getLogger(__name__)
settings = get_settings()


def gen_order_no(user_id: int) -> str:
    from datetime import datetime

    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{user_id:06d}{ts}{random.randint(0, 999999):06d}"


def create_payment(db: Session, order: Order, pay_type: str) -> dict:
    """返回前端拉起收银台所需的支付参数。"""
    if settings.payment_mode == "mock":
        return {"mock": True, "order_no": order.order_no}
    client = _wechat_client()
    description = "AI展示面-69解锁包" if order.order_type == "unlock" else "AI展示面-余额充值"
    if pay_type == "native":
        code_url = client.create_native(order.order_no, order.amount, description)
        return {"code_url": code_url}
    h5_url = client.create_h5(order.order_no, order.amount, description)
    return {"h5_url": h5_url}


def settle_paid_order(db: Session, order_no: str, out_trade_no: str, amount_paid: int) -> tuple[bool, str]:
    """支付到账幂等入账。

    验收链：验签 & 金额校验在入口（回调/mock-confirm）完成后进入本函数；
    幂等：order.status 先判后置于行锁内，重复回调不会重复加钱。
    """
    order = db.execute(select(Order).where(Order.order_no == order_no).with_for_update()).scalar_one_or_none()
    if order is None:
        return False, "未知订单"
    if order.status == "paid":
        return True, "OK"  # 幂等：已处理
    if order.status != "pending":
        return False, f"订单状态异常: {order.status}"
    if order.amount != amount_paid:
        return False, "金额不符"

    order.status = "paid"
    order.out_trade_no = out_trade_no
    from app.core.timeutil import utcnow

    order.paid_at = utcnow()

    user = lock_user(db, order.user_id)
    if order.order_type == "unlock":
        user.unlocked = True
    user.credits += order.credits

    db.add(
        BalanceTransaction(
            user_id=user.id,
            amount=order.credits,
            balance_after=user.credits,
            type="unlock" if order.order_type == "unlock" else "recharge",
            ref_id=order.id,
            remark="69 元解锁包" if order.order_type == "unlock" else "余额充值",
        )
    )
    db.commit()
    logger.info("settled order=%s type=%s credits=%s", order_no, order.order_type, order.credits)
    return True, "OK"


def handle_wechat_notify(db: Session, headers: dict, body: bytes) -> tuple[bool, str]:
    """微信回调处理器：验签 → 解密 → 幂等入账；失败返回 (False, reason)。"""
    try:
        client = _wechat_client()
        data = client.verify_and_decrypt(headers, body)
    except Exception as exc:  # 验签/解密失败
        logger.warning("wechat notify verify failed: %s", exc)
        return False, "验签失败"

    out_trade_no = data.get("out_trade_no", "")
    transaction_id = data.get("transaction_id") or uuid.uuid4().hex
    total = (data.get("amount") or {}).get("total") or 0
    return settle_paid_order(db, out_trade_no, transaction_id, total)


def _wechat_client():
    from app.services.wechat_pay_v3 import WechatPayV3Client, WechatPayV3Error

    if not (settings.wechat_mchid and settings.wechat_private_key_path):
        raise WechatPayV3Error("PAYMENT_MODE=wechat 但未配置 wechat_mchid/wechat_private_key_path")
    return WechatPayV3Client(settings)