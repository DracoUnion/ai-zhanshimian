"""AIGC 图生图适配器（可插拔）。

- mock：本地生成占位图，便于开发/联调，不产生第三方费用；
- openai：真实生图一律通过 `OpenAIClient.call_tti`（OpenAI 兼容底座，
  支持 gpt-image 系模型的参考图 img2img）。

对齐详细设计「第三方 AIGC 接入用适配器隔离，换平台只改一处」；
本项目所有 LLM / AIGC 调用统一走 `app/ai/openai_client.OpenAIClient`。
"""
from __future__ import annotations

import io
import random
import time
from functools import lru_cache

import openai

from ai.openai_client import OpenAIClient
from config import get_settings

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


class OpenAIAIGCService(AIGCService):
    """真实生图：通过 OpenAIClient.call_tti 逐张生成（支持参考图 img2img）。"""

    def __init__(self, api_key: str, base_url: str, model: str, size: str, retry: int = 3):
        self.client = OpenAIClient(
            api_key=api_key or "EMPTY",
            base_url=base_url or None,
            timeout=openai.Timeout(connect=60, read=180, write=None, pool=None),
        )
        self.model = model
        self.size = size
        self.retry = retry

    def transform(self, *, selfie, prompt, reference=None, n=1):
        images: list[bytes] = []
        for _ in range(n):
            blob = self.client.call_tti_retry(
                text=prompt or "",
                model_name=self.model,
                size=self.size,
                ref_img=selfie if selfie else reference,
                retry=self.retry,
                nothrow=False,
            )
            if not blob:
                raise RuntimeError("生图返回为空")
            images.append(blob)
        return images


@lru_cache
def get_aigc() -> AIGCService:
    if settings.aigc_provider == "openai":
        return OpenAIAIGCService(
            api_key=settings.aigc_http_token,
            base_url=settings.aigc_http_url,
            model=settings.aigc_model,
            size=settings.aigc_image_size,
            retry=settings.aigc_tti_retry,
        )
    return MockAIGCService(settings.aigc_mock_delay)