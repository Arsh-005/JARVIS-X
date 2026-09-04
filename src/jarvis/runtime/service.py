from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from jarvis.config import get_settings
from jarvis.llm import ProviderRouter
from jarvis.runtime.engine import AgentRuntime
from jarvis.runtime.llm_decision import LLMDecisionProvider
from jarvis.runtime.state import AgentState, Budget
from jarvis.tools import TOOLS, execute_tool


class RuntimeService:
    def __init__(self, session_id: str, confirm_token: str | None = None) -> None:
        self.session_id = session_id
        self.confirm_token = confirm_token
        settings = get_settings()
        self.state_budget = Budget(
            max_steps=settings.max_agent_steps,
            max_tool_calls=settings.max_tool_calls,
            max_elapsed_seconds=max(settings.llm_timeout_seconds * 2, 60),
            max_prompt_chars=max(settings.max_context_chars * 8, 20_000),
        )
        tool_specs = [
            {"name": t.name, "description": t.description, "writes": t.writes} for t in TOOLS.values()
        ]

        async def runner(name: str, args: dict[str, Any]) -> dict[str, Any]:
            result, token = await execute_tool(name, args, self.session_id, self.confirm_token)
            payload = {"output": result}
            if token:
                payload["confirmation_token"] = token
            return payload

        async def approval(name: str, args: dict[str, Any]) -> bool:
            # execute_tool remains the final authority and will return a scoped confirmation token.
            return True

        self.runtime = AgentRuntime(LLMDecisionProvider(ProviderRouter().get()), runner, approval, tool_specs)

    def new_state(self, goal: str) -> AgentState:
        return AgentState(goal=goal, session_id=self.session_id, budget=self.state_budget)

    async def run(self, goal: str) -> AgentState:
        return await self.runtime.run(self.new_state(goal))

    async def stream(self, goal: str) -> AsyncIterator[dict[str, Any]]:
        state = self.new_state(goal)
        async for event in self.runtime.stream(state):
            yield event
