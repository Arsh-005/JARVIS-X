from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import uuid4


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(slots=True)
class PlanStep:
    objective: str
    tool_hint: str | None = None
    depends_on: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))
    status: StepStatus = StepStatus.PENDING
    result: str | None = None


@dataclass(slots=True)
class Plan:
    goal: str
    steps: list[PlanStep]
    id: str = field(default_factory=lambda: str(uuid4()))

    def validate(self) -> None:
        if not self.steps:
            raise ValueError("plan must contain at least one step")
        ids = {s.id for s in self.steps}
        if len(ids) != len(self.steps):
            raise ValueError("duplicate step id")
        for step in self.steps:
            missing = set(step.depends_on) - ids
            if missing:
                raise ValueError(f"unknown dependencies: {sorted(missing)}")
        graph = {s.id: list(s.depends_on) for s in self.steps}
        visiting: set[str] = set()
        visited: set[str] = set()

        def dfs(node: str) -> None:
            if node in visiting:
                raise ValueError("dependency cycle detected")
            if node in visited:
                return
            visiting.add(node)
            for dep in graph[node]:
                dfs(dep)
            visiting.remove(node)
            visited.add(node)

        for node in graph:
            dfs(node)

    def next_ready(self) -> PlanStep | None:
        done = {s.id for s in self.steps if s.status in {StepStatus.DONE, StepStatus.SKIPPED}}
        for step in self.steps:
            if step.status == StepStatus.PENDING and set(step.depends_on) <= done:
                return step
        return None
