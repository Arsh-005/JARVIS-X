from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any


class JWTService:
    def __init__(self, secret: str, issuer: str = "jarvis-x", audience: str = "jarvis-api") -> None:
        if len(secret) < 32:
            raise ValueError("JWT secret must be at least 32 characters")
        self.secret = secret
        self.issuer = issuer
        self.audience = audience

    def issue(self, subject: str, roles: list[str], expires_minutes: int = 60) -> str:
        try:
            import jwt
        except ImportError as exc:
            raise RuntimeError("Install the 'auth' extra to use JWT authentication") from exc
        now = datetime.now(UTC)
        claims = {
            "sub": subject,
            "roles": roles,
            "iss": self.issuer,
            "aud": self.audience,
            "iat": now,
            "exp": now + timedelta(minutes=expires_minutes),
        }
        return jwt.encode(claims, self.secret, algorithm="HS256")

    def verify(self, token: str) -> dict[str, Any]:
        try:
            import jwt
        except ImportError as exc:
            raise RuntimeError("Install the 'auth' extra to use JWT authentication") from exc
        return jwt.decode(
            token, self.secret, algorithms=["HS256"], issuer=self.issuer, audience=self.audience
        )
