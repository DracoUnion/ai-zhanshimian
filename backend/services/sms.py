"""短信适配器：mock（打印+存开发码） / http（通用网关）。"""
from __future__ import annotations

import logging
from functools import lru_cache

import httpx

from app.config import get_settings
from app.core.cache import get_kv

logger = logging.getLogger(__name__)
settings = get_settings()


class SMSService:
    def send(self, phone: str, code: str) -> None:  # noqa: D102
        raise NotImplementedError


class MockSMSService(SMSService):
    """开发模式：打印验证码并写入 KV，便于联调（dev-code 接口取用）。"""

    def __init__(self):
        self.kv = get_kv()

    def send(self, phone, code):
        logger.info("【mock 短信】to=%s code=%s", phone, code)
        self.kv.set(f"dev_sms:{phone}", code, ttl=settings.sms_code_ttl)


class HttpSMSService(SMSService):
    """通用 HTTP 短信网关：POST {json:{phone,code}}，Authorization: Bearer token。"""

    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token

    def send(self, phone, code):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        resp = httpx.post(self.url, json={"phone": phone, "code": code}, headers=headers, timeout=10)
        resp.raise_for_status()


@lru_cache
def get_sms() -> SMSService:
    if settings.sms_provider == "http":
        return HttpSMSService(settings.sms_http_url, settings.sms_http_token)
    return MockSMSService()