from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import asdict
from typing import Any, Protocol

from jarvis.runtime.checkpoints import CheckpointStore
from jarvis.runtime.state import AgentState, RunStatus


class DecisionProvider(Protocol):
    async def decide(self, state: AgentState, tools: list[dict[str, Any]]) -> dict[str, Any]: ...


ToolRunner = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]
ApprovalCheck = Callable[[str, dict[str, Any]], Awaitable[bool]]


class AgentRuntime:
    def __init__(
        self,
        decision_provider: DecisionProvider,
        tool_runner: ToolRunner,
        approval_check: ApprovalCheck,
        tools: list[dict[str, Any]],
        checkpoint_store: CheckpointStore | None = None,
    ) -> None:
        self.decision_provider = decision_provider
        self.tool_runner = tool_runner
        self.approval_check = approval_check
        self.tools = tools
        self.checkpoints = checkpoint_store or CheckpointStore()

    async def run(self, state: AgentState) -> AgentState:
        async for _ in self.stream(state):
            pass
        return state

    async def stream(self, state: AgentState) -> AsyncIterator[dict[str, Any]]:
        state.status = RunStatus.RUNNING
        state.add_event("run_started", goal=state.goal)
        yield {"event": "run_started", "run_id": state.run_id}
        try:
            while state.status == RunStatus.RUNNING:
                state.budget.assert_available()
                state.budget.steps += 1
                decision = await asyncio.wait_for(
                    self.decision_provider.decide(state, self.tools), timeout=30
                )
                state.budget.prompt_chars += len(json.dumps(decision, default=str))
                kind = str(decision.get("type", "final"))
                if kind == "final":
                    state.final_answer = str(decision.get("answer", ""))
                    state.status = RunStatus.COMPLETED
                    state.add_event("final", answer=state.final_answer)
                    yield {"event": "final", "answer": state.final_answer}
                    break
                if kind != "tool":
                    raise RuntimeError(f"unsupported decision type: {kind}")
                tool = str(decision.get("tool", ""))
                args = dict(decision.get("args") or {})
                if state.fingerprint_action(tool, args):
                    state.status = RunStatus.LOOP_DETECTED
                    state.error = f"repeated action detected: {tool}"
                    yield {"event": "loop_detected", "tool": tool}
                    break
                if not await self.approval_check(tool, args):
                    state.status = RunStatus.WAITING_APPROVAL
                    state.add_event("approval_required", tool=tool, args=args)
                    yield {"event": "approval_required", "tool": tool, "args": args}
                    break
                state.budget.tool_calls += 1
                result = await self.tool_runner(tool, args)
                state.observations.append({"tool": tool, "args": args, "result": result})
                state.add_event("tool_result", tool=tool, result=result)
                yield {"event": "tool_result", "tool": tool, "result": result}
                self.checkpoints.save(state.run_id, asdict(state))
        except RuntimeError as exc:
            if "budget exhausted" in str(exc):
                state.status = RunStatus.BUDGET_EXHAUSTED
            else:
                state.status = RunStatus.FAILED
            state.error = str(exc)
            yield {"event": "error", "error": state.error}
        except Exception as exc:
            state.status = RunStatus.FAILED
            state.error = f"{type(exc).__name__}: {exc}"
            yield {"event": "error", "error": state.error}
