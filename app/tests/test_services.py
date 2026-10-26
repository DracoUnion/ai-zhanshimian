"""服务层冒烟测试：本机账户 → 试用生成 → 解锁/充值 → 付费生成幂等与扣费。

运行：python -m pytest app/tests -v
"""
from __future__ import annotations

import pytest

from app.core.errors import BizError, ErrCode
from app.services import facade as svc
from app.tasks.generation_exec import run_generation


def _upload(kind="selfie") -> dict:
    return svc.upload_image(kind, b"\xff\xd8mock-jpeg-content", "image/jpeg")


def _run_gen(gen_id: int) -> None:
    run_generation(gen_id)


# ---------- 基础状态 / 模板 ----------
def test_initial_local_state(fresh_db):
    state = svc.state()
    assert state["credits"] == 0
    assert state["unlocked"] is False
    assert state["trial_used"] is False
    assert state["trial_available"] is True


def test_templates_seeded(fresh_db):
    items = svc.templates()
    assert len(items) >= 5
    first = items[0]
    assert first["name"]
    assert first["prompt_template"]


# ---------- 试用生成 ----------
def test_trial_generation_flow(fresh_db, sync_generation):
    up = dict(_upload())
    result = svc.create_generation(
        selfie_key=up["object_key"],
        template_id=1,
        quantity=1,
        idempotency_key="k-trial-1",
    )
    assert result["credit_cost"] == 0
    assert result["trial_used"] is True
    assert result["balance"] == 0

    _run_gen(result["generation_id"])
    detail = svc.generation_detail(result["generation_id"])
    assert detail["status"] == "success"
    assert len(detail["results"]) == 1

    # 试用已用、无余额 → 未解锁再次生成应报 FEATURE_LOCKED
    with pytest.raises(BizError) as ei:
        svc.create_generation(selfie_key=up["object_key"], template_id=1, quantity=1, idempotency_key="k-trial-2")
    assert ei.value.code == ErrCode.FEATURE_LOCKED


# ---------- 解锁 / 付费生成（本地一次性解锁，无充值无支付） ----------
def test_local_unlock_flow(fresh_db, sync_generation):
    assert not svc.state()["unlocked"]
    assert svc.state()["credits"] == 0
    result = svc.unlock()
    assert result["unlocked"] is True
    assert result["credits"] == 69
    assert svc.state()["unlocked"] is True
    assert svc.state()["credits"] == 69

    # 幂等：重复解锁不重复赠送
    again = svc.unlock()
    assert again["credits"] == 69
    assert svc.state()["credits"] == 69


def test_local_unlock_then_generation_flow(fresh_db, sync_generation):
    assert not svc.state()["trial_used"]
    svc.unlock()

    up = dict(_upload())

    # 未用过试用 → 首单优先免费试用（不扣费）
    r0 = svc.create_generation(selfie_key=up["object_key"], prompt="咖啡厅氛围", quantity=1, idempotency_key="k-0")
    assert r0["credit_cost"] == 0
    assert r0["trial_used"] is True
    assert svc.state()["credits"] == 69

    # 付费生成 quantity=2 → 扣 2
    r = svc.create_generation(selfie_key=up["object_key"], prompt="街头潮流感", quantity=2, idempotency_key="k-1")
    assert r["credit_cost"] == 2
    assert r["balance"] == 67
    _run_gen(r["generation_id"])
    detail = svc.generation_detail(r["generation_id"])
    assert detail["status"] == "success"
    assert len(detail["results"]) == 2
    assert svc.state()["credits"] == 67

    # 幂等键：重复提交不重复扣费、返回同一记录
    rdup = svc.create_generation(selfie_key=up["object_key"], prompt="街头潮流感", quantity=2, idempotency_key="k-1")
    assert rdup["generation_id"] == r["generation_id"]
    assert svc.state()["credits"] == 67


def test_balance_insufficient(fresh_db, sync_generation):
    svc.unlock()  # 69 次
    up = dict(_upload())
    svc.create_generation(selfie_key=up["object_key"], prompt="试用", quantity=1, idempotency_key="b-trial")
    # 已解锁且余额不足 12 → BALANCE_INSUFFICIENT
    for n in range(5):
        svc.create_generation(selfie_key=up["object_key"], prompt="消耗", quantity=12, idempotency_key=f"b-{n}")
    assert svc.state()["credits"] == 9
    with pytest.raises(BizError) as ei:
        svc.create_generation(selfie_key=up["object_key"], prompt="超额", quantity=12, idempotency_key="b-over")
    assert ei.value.code == ErrCode.BALANCE_INSUFFICIENT


# ---------- 历史列表 / 删除 ----------
def test_generation_list_and_delete(fresh_db, sync_generation):
    up = dict(_upload())
    r = svc.create_generation(selfie_key=up["object_key"], template_id=2, quantity=1, idempotency_key="k-list-1")
    _run_gen(r["generation_id"])

    listing = svc.generation_list(1, 20)
    assert listing["total"] == 1
    assert listing["items"][0]["generation_id"] == r["generation_id"]
    assert listing["items"][0]["template_name"]

    svc.delete_generation(r["generation_id"])
    assert svc.generation_list(1, 20)["total"] == 0


# ---------- 参数校验 / 越权 ----------
def test_input_validation(fresh_db):
    # 图片来源非法（非本机账户命名空间）
    with pytest.raises(BizError) as ei:
        svc.create_generation(selfie_key="u/999/x.jpg", template_id=1, quantity=1)
    assert ei.value.code == ErrCode.UPLOAD_INVALID

    # 非法图片类型
    with pytest.raises(BizError) as ei:
        svc.upload_image("selfie", b"data", "text/plain")
    assert ei.value.code == ErrCode.UPLOAD_INVALID