"""KV 缓存抽象：内存实现（开发）与 Redis 实现（生产）可切换。

Redis Key 约定（对齐详细设计）：
  sms:{phone}        验证码              TTL 300s
  sms_cooldown:{phone} 发送冷却           TTL 60s
  dev_sms:{phone}     mock 短信码(仅开发)  TTL 300s
  rl:gen:{user_id}    生成接口限流        TTL 60s
"""
from __future__ import annotations

import threading
import time
from functools import lru_cache

from ..config import get_settings
from .timeutil import coerce_aware  # noqa: F401  （保持时间语义一致）

settings = get_settings()


class KV:
    def get(self, key: str):  # noqa: D102
        raise NotImplementedError

    def set(self, key: str, value, ttl: int | None = None):  # noqa: D102
        raise NotImplementedError

    def delete(self, key: str):  # noqa: D102
        raise NotImplementedError

    def incr(self, key: str, ttl: int | None = None) -> int:  # noqa: D102
        raise NotImplementedError


class MemoryKV(KV):
    """进程内 KV（带过期）。单进程开发可用；多 worker/生产请配置 REDIS_URL。"""

    def __init__(self) -> None:
        self._data: dict[str, tuple] = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            value, expire_at = item
            if expire_at is not None and expire_at < time.time():
                self._data.pop(key, None)
                return None
            return value

    def set(self, key, value, ttl=None):
        expire_at = time.time() + ttl if ttl else None
        with self._lock:
            self._data[key] = (value, expire_at)

    def delete(self, key):
        with self._lock:
            self._data.pop(key, None)

    def incr(self, key, ttl=None):
        with self._lock:
            cur = self.get(key) or 0
            nxt = int(cur) + 1
            self.set(key, nxt, ttl=ttl)
            return nxt


class RedisKV(KV):
    """Promiseless 同步 Redis 客户端。"""

    def __init__(self, url: str) -> None:
        import redis  # 惰性导入，未装 redis 也可使用 MemoryKV

        self._r = redis.Redis.from_url(url, decode_responses=True)

    def get(self, key):
        return self._r.get(key)

    def set(self, key, value, ttl=None):
        self._r.set(key, value, ex=ttl)

    def delete(self, key):
        self._r.delete(key)

    def incr(self, key, ttl=None):
        val = self._r.incr(key)
        if ttl:
            self._r.expire(key, ttl)
        return val


@lru_cache
def get_kv() -> KV:
    if settings.redis_url:
        return RedisKV(settings.redis_url)
    return MemoryKV()