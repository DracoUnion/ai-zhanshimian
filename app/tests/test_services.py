"""服务层冒烟测试：免费无限次生成（试用/解锁/扣费/余额已彻底移除）。

运行：python -m pytest app/tests -v
"""
from __future__ import annotations

import pytest

from core.errors import BizError, ErrCode
from services import facade as svc
from tasks.generation_exec import run_generation


def _upload(kind="selfie") -> dict:
    return svc.upload_image(kind, b"\xff\xd8mock-jpeg-content", "image/jpeg")


def _run_gen(gen_id: int) -> None:
    run_generation(gen_id)


# ---------- 基础状态 / 模板 ----------
def test_initial_local_state(fresh_db):
    state = svc.state()
    assert state["user_id"] > 0
    assert state["nickname"] is None


def test_templates_seeded(fresh_db):
    items = svc.templates()
    assert len(items) >= 5
    first = items[0]
    assert first["name"]
    assert first["prompt_template"]


# ---------- 免费无限次生成 ----------
def test_generation_flow(fresh_db, sync_generation):
    up = dict(_upload())
    result = svc.create_generation(
        selfie_key=up["object_key"],
        template_id=1,
        quantity=2,
        idempotency_key="k-1",
    )
    assert result["status"] == "pending"
    assert result["quantity"] == 2

    _run_gen(result["generation_id"])
    detail = svc.generation_detail(result["generation_id"])
    assert detail["status"] == "success"
    assert len(detail["results"]) == 2

    # 连续第二次生成仍成功（无限次）
    result2 = svc.create_generation(
        selfie_key=up["object_key"],
        template_id=2,
        quantity=1,
        idempotency_key="k-2",
    )
    _run_gen(result2["generation_id"])
    assert svc.generation_detail(result2["generation_id"])["status"] == "success"


def test_generation_idempotency_key(fresh_db, sync_generation):
    up = dict(_upload())
    r1 = svc.create_generation(selfie_key=up["object_key"], prompt="街拍", quantity=1, idempotency_key="dup-1")
    r2 = svc.create_generation(selfie_key=up["object_key"], prompt="街拍", quantity=1, idempotency_key="dup-1")
    assert r2["generation_id"] == r1["generation_id"]
    assert svc.generation_list(1, 20)["total"] == 1


def test_custom_prompt_generation(fresh_db, sync_generation):
    up = dict(_upload())
    result = svc.create_generation(selfie_key=up["object_key"], prompt="海边日落，暖光氛围", quantity=1)
    _run_gen(result["generation_id"])
    detail = svc.generation_detail(result["generation_id"])
    assert detail["status"] == "success"
    assert detail["prompt"] == "海边日落，暖光氛围"


# ---------- 历史列表 / 删除 ----------
def test_generation_list_and_delete(fresh_db, sync_generation):
    up = dict(_upload())
    r = svc.create_generation(selfie_key=up["object_key"], template_id=2, quantity=1)
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

    # template_id 与 prompt 至少其一
    with pytest.raises(Exception):
        svc.create_generation(selfie_key="u/1/x.jpg", quantity=1)