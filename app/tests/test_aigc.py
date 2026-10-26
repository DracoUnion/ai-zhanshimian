"""AIGC / OpenAIClient 接线测试（离线，不产生真实网络调用）。

验证：所有真实生图走 OpenAIClient.call_tti；mock 提供方保持离线可用。
"""
from __future__ import annotations

import pytest


def test_openai_client_class_api():
    """OpenAIClient 类可用且保留 LLM/AIGC 调用方法。"""
    from ai.openai_client import OpenAIClient

    client = OpenAIClient(api_key="test", base_url=None)
    for name in ("call_llm", "call_llm_retry", "call_vlm_retry", "call_tti", "call_tti_retry"):
        assert callable(getattr(client, name)), name


def test_mock_provider_offline():
    """default/mock 生图不依赖 API，且返回 n 张 JPEG。"""
    from services import aigc

    svc = aigc.get_aigc()
    assert isinstance(svc, aigc.MockAIGCService)
    out = svc.transform(selfie=b"x", prompt="海边", n=2)
    assert len(out) == 2
    assert all(b.startswith(b"\xff\xd8") for b in out)  # JPEG magic


def test_openai_provider_goes_through_OpenAIClient(fresh_db):
    """AIGC_PROVIDER=openai 时，transform 逐张走 OpenAIClient.call_tti。"""
    from services import aigc

    svc = aigc.OpenAIAIGCService(api_key="k", base_url="http://127.0.0.1:9", model="gpt-image-1", size="1024x1024")
    assert isinstance(svc.client, aigc.OpenAIClient)

    captured: dict = {}

    def fake_tti(text, model_name, size, ref_img, **kw):
        captured.update(text=text, model=model_name, ref=ref_img)
        return b"\xff\xd8fake"

    svc.client.call_tti_retry = fake_tti  # 替换为 fake，避免网络
    out = svc.transform(selfie=b"img", prompt="海边氛围", reference=None, n=1)
    assert len(out) == 1
    assert out[0] == b"\xff\xd8fake"
    assert captured["model"] == "gpt-image-1"
    assert captured["ref"] == b"img"  # 自拍作参考图传入