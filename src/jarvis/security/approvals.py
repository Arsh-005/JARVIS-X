from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass


@dataclass(slots=True)
class ApprovalTokenManager:
    secret: str
    ttl_seconds: int = 300

    def issue(self, tool: str, args: dict) -> str:
        ts = str(int(time.time()))
        payload = json.dumps({"tool": tool, "args": args}, sort_keys=True, separators=(",", ":"))
        sig = hmac.new(self.secret.encode(), f"{ts}.{payload}".encode(), hashlib.sha256).hexdigest()
        return f"{ts}.{sig}"


def verify(
    self,
    token: str,
    tool: str,
    args: dict,
) -> bool:
    try:
        ts_s, _ = token.split(".", 1)
        ts = int(ts_s)

    except Exception:
        return False

    if abs(time.time() - ts) > self.ttl_seconds:
        return False

    expected = self.issue_with_timestamp(
        tool,
        args,
        ts,
    )

    return hmac.compare_digest(
        token,
        expected,
    )

    def issue_with_timestamp(self, tool: str, args: dict, ts: int) -> str:
        payload = json.dumps({"tool": tool, "args": args}, sort_keys=True, separators=(",", ":"))
        sig = hmac.new(self.secret.encode(), f"{ts}.{payload}".encode(), hashlib.sha256).hexdigest()
        return f"{ts}.{sig}"
