"""余额账本：credits 变更与流水同事务（对应详细设计 5.1/5.3）。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.balance import BalanceTransaction
from app.models.generation import Generation
from app.models.user import User


def lock_user(db: Session, user_id: int) -> User:
    return db.execute(select(User).where(User.id == user_id).with_for_update()).scalar_one()


def record_balance(
    db: Session,
    user_id: int,
    amount: int,
    tx_type: str,
    *,
    balance_after: int,
    ref_id: int | None = None,
    remark: str | None = None,
) -> BalanceTransaction:
    tx = BalanceTransaction(
        user_id=user_id,
        amount=amount,
        balance_after=balance_after,
        type=tx_type,
        ref_id=ref_id,
        remark=remark,
    )
    db.add(tx)
    return tx


def add_balance(
    db: Session,
    user_id: int,
    amount: int,
    tx_type: str,
    *,
    ref_id: int | None = None,
    remark: str | None = None,
) -> User:
    """行锁追加余额并记流水。amount 必须为正（扣减请用专属流程）。"""
    assert amount > 0, "add_balance amount 必须为正"
    user = lock_user(db, user_id)
    user.credits += amount
    record_balance(db, user_id, amount, tx_type, balance_after=user.credits, ref_id=ref_id, remark=remark)
    db.flush()
    return user


def refund_generation(db: Session, gen: Generation) -> None:
    """生成失败退款（associates charged 才退，防重复）。"""
    if gen.charged and gen.credit_cost > 0:
        user = lock_user(db, gen.user_id)
        user.credits += gen.credit_cost
        record_balance(
            db,
            gen.user_id,
            gen.credit_cost,
            "refund",
            balance_after=user.credits,
            ref_id=gen.id,
            remark="生成失败自动退回",
        )
        gen.charged = False
        db.flush()