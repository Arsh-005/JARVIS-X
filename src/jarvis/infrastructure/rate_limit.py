from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import RLock


@dataclass
class TokenBucket:
    rate_per_second: float
    capacity: float
    tokens: float | None = None
    updated_at: float = field(default_factory=time.monotonic)
    _lock: RLock = field(default_factory=RLock)

    def __post_init__(self) -> None:
        if self.tokens is None:
            self.tokens = self.capacity

    def allow(self, cost: float = 1.0) -> bool:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.updated_at
            self.updated_at = now
            self.tokens = min(self.capacity, float(self.tokens) + elapsed * self.rate_per_second)
            if self.tokens < cost:
                return False
            self.tokens -= cost
            return True
