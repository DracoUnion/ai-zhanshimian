"""冒烟测试：跑通「注册 → 试用生成 → 充值 → 解锁 → 生成扣费」主链路。

基于 mock 适配器（payments/sms/aigc/local storage）与 SQLite，不依赖任何外部服务。
运行：python -m pytest app/tests -v
"""
from __future__ import annotations

import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="zhanshi_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["PAYMENT_MODE"] = "mock"
os.environ["SMS_PROVIDER"] = "mock"
os.environ["AIGC_PROVIDER"] = "mock"
os.environ["AIGC_MOCK_DELAY"] = "0"
os.environ["STORAGE_PROVIDER"] = "local"
os.environ["STORAGE_LOCAL_DIR"] = os.path.join(_tmp, "storage")
os.environ["CELERY_EAGER"] = "true"
os.environ["SEED_DEMO_TEMPLATES"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _login(client, phone="13800138000"):
    client.post("/api/v1/auth/sms-code", json={"phone": phone})
    code = client.post("/api/v1/auth/dev-code", json={"phone": phone}).json()["data"]["code"]
    resp = client.post("/api/v1/auth/phone-login", json={"phone": phone, "code": code})
    assert resp.status_code == 200, resp.text
    token = resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return headers


def _upload(client, headers, kind="selfie", uid=1):
    r = client.post("/api/v1/uploads/presign", json={"kind": kind, "content_type": "image/jpeg", "size": 1024}, headers=headers)
    assert r.status_code == 200
    data = r.json()["data"]
    # 本地直传
    put = client.put(data["upload_url"], content=b"\xff\xd8testjpeg", headers=headers)
    assert put.status_code == 200, put.text
    return data["object_key"]


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["code"] == 0


def test_register_and_trial_generation(client):
    headers = _login(client)

    # 新用户：未解锁、0 余额、可用试用
    me = client.get("/api/v1/users/me", headers=headers).json()["data"]
    assert me["unlocked"] is False
    assert me["credits"] == 0
    assert me["trial_available"] is True

    # 上传自拍并生成（免费试用，eager 内联完成）
    selfie = _upload(client, headers, "selfie", uid=me["id"])
    r = client.post(
        "/api/v1/generations",
        json={"selfie_key": selfie, "template_id": 1, "quantity": 1},
        headers={**headers, "Idempotency-Key": "k-trial-1"},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["credit_cost"] == 0
    assert data["trial_used"] is True

    # 任务应已内联跑完 → success
    detail = client.get(f"/api/v1/generations/{data['generation_id']}", headers=headers).json()["data"]
    assert detail["status"] == "success"
    assert len(detail["results"]) == 1

    # 试用已用、无余额——再次生成应报未解锁
    r2 = client.post(
        "/api/v1/generations",
        json={"selfie_key": selfie, "template_id": 1, "quantity": 1},
        headers={**headers, "Idempotency-Key": "k-trial-2"},
    )
    assert r2.json()["code"] == 1206  # FEATURE_LOCKED


def test_unlock_and_recharge_generation_flow(client):
    headers = _login(client, phone="13800138001")
    me = client.get("/api/v1/users/me", headers=headers).json()["data"]

    # 购买 69 解锁包 → mock 到账
    order = client.post(
        "/api/v1/payments/recharge",
        json={"amount": 6900, "order_type": "unlock", "pay_type": "h5"},
        headers=headers,
    )
    assert order.status_code == 200, order.text
    order_no = order.json()["data"]["order_no"]

    confirm = client.post("/api/v1/payments/mock-confirm", json={"order_no": order_no}, headers=headers)
    assert confirm.status_code == 200, confirm.text

    me = client.get("/api/v1/users/me", headers=headers).json()["data"]
    assert me["unlocked"] is True
    assert me["credits"] == 69  # 赠送次数

    # 充值 50 元
    order2 = client.post(
        "/api/v1/payments/recharge",
        json={"amount": 5000, "order_type": "recharge", "pay_type": "h5"},
        headers=headers,
    ).json()["data"]
    assert client.post("/api/v1/payments/mock-confirm", json={"order_no": order2["order_no"]}, headers=headers).status_code == 200
    me = client.get("/api/v1/users/me", headers=headers).json()["data"]
    assert me["credits"] == 119

    # 支付回调幂等：重复 confirm 不加钱
    dup = client.post("/api/v1/payments/mock-confirm", json={"order_no": order2["order_no"]}, headers=headers)
    assert dup.status_code == 200
    me = client.get("/api/v1/users/me", headers=headers).json()["data"]
    assert me["credits"] == 119

    # 未用过试用 → 首单仍优先消耗免费试用（不扣费）；随后一次才走付费
    selfie = _upload(client, headers, "selfie", uid=me["id"])
    r0 = client.post(
        "/api/v1/generations",
        json={"selfie_key": selfie, "prompt": "咖啡厅氛围", "quantity": 1},
        headers={**headers, "Idempotency-Key": "k-trial-paid-1"},
    )
    assert r0.status_code == 200, r0.text
    assert r0.json()["data"]["credit_cost"] == 0
    assert r0.json()["data"]["trial_used"] is True
    me = client.get("/api/v1/users/me", headers=headers).json()["data"]
    assert me["credits"] == 119  # 试用单未扣

    # 付费生成 quantity=2 → 扣 2
    r = client.post(
        "/api/v1/generations",
        json={"selfie_key": selfie, "prompt": "街头潮流感", "quantity": 2},
        headers={**headers, "Idempotency-Key": "k-paid-1"},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["credit_cost"] == 2
    assert data["balance"] == 117

    detail = client.get(f"/api/v1/generations/{data['generation_id']}", headers=headers).json()["data"]
    assert detail["status"] == "success"
    assert len(detail["results"]) == 2

    # 重复 Idempotency-Key 不重复扣费
    rdup = client.post(
        "/api/v1/generations",
        json={"selfie_key": selfie, "prompt": "街头潮流感", "quantity": 2},
        headers={**headers, "Idempotency-Key": "k-paid-1"},
    )
    assert rdup.json()["data"]["generation_id"] == data["generation_id"]


def test_admin_grant_gift(client):
    headers = _login(client, phone="13800138002")
    uid = client.get("/api/v1/users/me", headers=headers).json()["data"]["id"]
    r = client.post(
        f"/api/v1/admin/users/{uid}/credits",
        json={"credits": 30, "remark": "老用户权益补发"},
        headers={"X-Admin-Key": "change-me-admin"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["balance"] == 30
    me = client.get("/api/v1/users/me", headers=headers).json()["data"]
    assert me["credits"] == 30


def test_auth_errors(client):
    r = client.post("/api/v1/auth/phone-login", json={"phone": "13800138003", "code": "000000"})
    assert r.status_code == 400
    assert r.json()["code"] == 1102

    r = client.get("/api/v1/users/me")
    assert r.status_code == 401
    assert r.json()["code"] == 1001