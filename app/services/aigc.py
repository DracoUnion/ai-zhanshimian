"""AIGC 图生图适配器（可插拔）。

- mock：本地生成占位图，便于开发/联调，不产生第三方费用。
- http：通用 HTTP 网关适配（需对接实际 AIGC 平台时在此实现具体协议）。

对齐详细设计「第三方 AIGC 接入用适配器隔离，换平台只改一处」。
"""
from __future__ import annotations

import base64
import io
import random
import time
from functools import lru_cache

import httpx

from app.config import get_settings

settings = get_settings()


class AIGCService:
    def transform(self, *, selfie: bytes, prompt: str, reference: bytes | None = None, n: int = 1) -> list[bytes]:  # noqa: D102
        raise NotImplementedError


class MockAIGCService(AIGCService):
    """本地模拟：随机配色占位图 + 提示词首段文字。"""

    def __init__(self, delay: float):
        self.delay = delay

    def transform(self, *, selfie, prompt, reference=None, n=1):
        if self.delay > 0:
            time.sleep(self.delay)
        from PIL import Image, ImageDraw  # 惰性导入

        images: list[bytes] = []
        for i in range(n):
            w, h = 640, 853
            img = Image.new("RGB", (w, h), (random.randint(40, 220), random.randint(40, 220), random.randint(40, 220)))
            draw = ImageDraw.Draw(img)
            text = (prompt or "AI 展示面").strip()[:20] or "AI 展示面"
            draw.text((20, 20), f"#{i + 1} {text}", fill="white")
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=82)
            images.append(buf.getvalue())
        return images


class HttpAIGCService(AIGCService):
    """通用 HTTP 网关适配。对接真实平台时按平台协议改写 payload/响应解析。"""

    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token

    def transform(self, *, selfie, prompt, reference=None, n=1):
        payload = {
            "images": [base64.b64encode(selfie).decode()],
            "prompt": prompt,
            "n": n,
        }
        if reference:
            payload["reference"] = base64.b64encode(reference).decode()
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        resp = httpx.post(self.url, json=payload, headers=headers, timeout=180)
        resp.raise_for_status()
        data = resp.json()
        return [base64.b64decode(img) for img in data["images"]]


@lru_cache
def get_aigc() -> AIGCService:
    if settings.aigc_provider == "http":
        return HttpAIGCService(settings.aigc_http_url, settings.aigc_http_token)
    return MockAIGCService(settings.aigc_mock_delay)