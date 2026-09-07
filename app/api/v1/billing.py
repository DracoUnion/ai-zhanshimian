"""计费/支付：下单、回调、订单查询、mock 到账模拟。"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import get_settings
from app.core.errors import BizError, ErrCode
from app.core.response import ok
from app.db.session import get_db
from app.models.order import Order
from app.models.user import User
from app.schemas.payment import CreatePaymentOut, MockConfirmReq, OrderOut, RechargeReq
from app.services.payment import create_payment, gen_order_no, handle_wechat_notify, settle_paid_order

router = APIRouter()
settings = get_settings()

_WECHAT_SUCCESS = "<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>"
_WECHAT_FAIL = "<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[FAIL]]></return_msg></xml>"


@router.post("/recharge")
def recharge(req: RechargeReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if req.order_type == "recharge":
        if req.amount not in settings.recharge_packages:
            raise BizError(ErrCode.ORDER_NOT_FOUND, "金额不在可选套餐内")
        credits = settings.recharge_packages[req.amount]
    else:  # unlock
        if req.amount != settings.unlock_price:
            raise BizError(ErrCode.ORDER_NOT_FOUND, "解锁包金额不正确")
        if user.unlocked:
            raise BizError(ErrCode.ORDER_STATUS_INVALID, "您已解锁，无需重复购买")
        credits = settings.welcome_credits

    order = Order(
        user_id=user.id,
        order_no=gen_order_no(user.id),
        order_type=req.order_type,
        amount=req.amount,
        credits=credits,
        pay_method=f"wechat_{req.pay_type}",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    pay_params = create_payment(db, order, req.pay_type)
    return ok(CreatePaymentOut(order_no=order.order_no, status=order.status, pay_params=pay_params).model_dump())


@router.post("/wechat/notify")
async def wechat_notify(request: Request, db: Session = Depends(get_db)):
    """微信异步回调（无统一响应包裹，返回微信指定 XML）。mock 模式下直接应答成功。"""
    if settings.payment_mode == "mock":
        return PlainTextResponse(_WECHAT_SUCCESS, media_type="application/xml")
    body = await request.body()
    headers = dict(request.headers)
    ok_, _msg = handle_wechat_notify(db, headers, body)
    return PlainTextResponse(_WECHAT_SUCCESS if ok_ else _WECHAT_FAIL, media_type="application/xml")


@router.post("/mock-confirm")
def mock_confirm(req: MockConfirmReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """仅开发/验收：模拟微信回调到账（幂等）。生产 PAYMENT_MODE=wechat 时禁用。"""
    if settings.payment_mode != "mock":
        raise BizError(ErrCode.FORBIDDEN, "仅在 mock 模式可用", status_code=403)
    order = db.scalar(select(Order).where(Order.order_no == req.order_no))
    if order is None or order.user_id != user.id:
        raise BizError(ErrCode.ORDER_NOT_FOUND, "订单不存在", status_code=404)
    paid = req.paid_amount if req.paid_amount is not None else order.amount
    ok_, msg = settle_paid_order(db, req.order_no, req.out_trade_no or uuid.uuid4().hex, paid)
    if not ok_:
        raise BizError(ErrCode.ORDER_STATUS_INVALID, msg)
    return ok({"order_no": req.order_no, "status": "paid"})


@router.get("/orders/{order_no}")
def order_status(order_no: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    order = db.scalar(select(Order).where(Order.order_no == order_no))
    if order is None or order.user_id != user.id:
        raise BizError(ErrCode.ORDER_NOT_FOUND, "订单不存在", status_code=404)
    return ok(OrderOut.model_validate(order).model_dump())