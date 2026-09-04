from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from threading import RLock
from typing import Any


class CacheBackend:
    def get(self, key: str) -> Any | None:
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError


@dataclass
class InMemoryCache(CacheBackend):
    _values: dict[str, tuple[float, Any]] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)

    def get(self, key: str) -> Any | None:
        now = time.time()
        with self._lock:
            item = self._values.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at <= now:
                self._values.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        with self._lock:
            self._values[key] = (time.time() + ttl_seconds, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._values.pop(key, None)


class RedisCache(CacheBackend):
    def __init__(self, url: str, prefix: str = "jarvis") -> None:
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError("Install the 'redis' extra to use RedisCache") from exc
        self._client = redis.Redis.from_url(url, decode_responses=True)
        self._prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    def get(self, key: str) -> Any | None:
        raw = self._client.get(self._key(key))
        return None if raw is None else json.loads(raw)

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        self._client.setex(self._key(key), ttl_seconds, json.dumps(value, default=str))

    def delete(self, key: str) -> None:
        self._client.delete(self._key(key))
