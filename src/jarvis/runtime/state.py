from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from time import monotonic
from typing import Any
from uuid import uuid4


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    BUDGET_EXHAUSTED = "budget_exhausted"
    LOOP_DETECTED = "loop_detected"


@dataclass(slots=True)
class Budget:
    max_steps: int = 12
    max_tool_calls: int = 8
    max_elapsed_seconds: float = 90.0
    max_prompt_chars: int = 120_000
    steps: int = 0
    tool_calls: int = 0
    prompt_chars: int = 0
    started_at: float = field(default_factory=monotonic)

    def assert_available(self) -> None:
        if self.steps >= self.max_steps:
            raise RuntimeError("step budget exhausted")
        if self.tool_calls >= self.max_tool_calls:
            raise RuntimeError("tool-call budget exhausted")
        if monotonic() - self.started_at >= self.max_elapsed_seconds:
            raise RuntimeError("time budget exhausted")
        if self.prompt_chars >= self.max_prompt_chars:
            raise RuntimeError("prompt budget exhausted")


@dataclass(slots=True)
class AgentEvent:
    kind: str
    payload: dict[str, Any]


@dataclass(slots=True)
class AgentState:
    goal: str
    session_id: str
    run_id: str = field(default_factory=lambda: str(uuid4()))
    status: RunStatus = RunStatus.CREATED
    messages: list[dict[str, str]] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    events: list[AgentEvent] = field(default_factory=list)
    seen_actions: dict[str, int] = field(default_factory=dict)
    budget: Budget = field(default_factory=Budget)
    final_answer: str | None = None
    error: str | None = None

    def add_event(self, kind: str, **payload: Any) -> None:
        self.events.append(AgentEvent(kind, payload))

    def fingerprint_action(self, tool: str, args: dict[str, Any]) -> bool:
        key = f"{tool}:{sorted(args.items())!r}"
        self.seen_actions[key] = self.seen_actions.get(key, 0) + 1
        return self.seen_actions[key] >= 3
