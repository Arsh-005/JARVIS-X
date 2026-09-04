from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class MemoryKind(StrEnum):
    WORKING = "working"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROJECT = "project"
    PREFERENCE = "preference"


@dataclass(slots=True)
class MemoryRecord:
    text: str
    kind: MemoryKind
    session_id: str
    importance: float = 0.5
    tags: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
