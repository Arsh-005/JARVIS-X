from __future__ import annotations

import hashlib
import hmac
import os

from fastapi import Header, HTTPException


def _configured_key() -> str:
    return os.getenv("JARVIS_API_KEY", "")


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = _configured_key()
    if not expected:
        return
    if not x_api_key or not hmac.compare_digest(
        hashlib.sha256(x_api_key.encode()).digest(), hashlib.sha256(expected.encode()).digest()
    ):
        raise HTTPException(status_code=401, detail="invalid API key")
