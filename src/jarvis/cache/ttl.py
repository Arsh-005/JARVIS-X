from __future__ import annotations

import time
from threading import RLock
from typing import Any


class TTLCache:
    def __init__(
        self,
        max_items: int = 256,
        ttl_seconds: int = 300,
    ) -> None:
        self.max_items = max_items
        self.ttl_seconds = ttl_seconds
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = RLock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._data.get(key)

            if not item:
                return None

            expires, value = item

            if expires < time.time():
                self._data.pop(key, None)
                return None

            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if len(self._data) >= self.max_items:
                oldest = min(
                    self._data,
                    key=lambda k: self._data[k][0],
                )
                self._data.pop(oldest, None)

            self._data[key] = (
                time.time() + self.ttl_seconds,
                value,
            )

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
