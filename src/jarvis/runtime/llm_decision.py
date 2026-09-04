from __future__ import annotations

from typing import Any

from jarvis.llm import LLMProvider, extract_json_object
from jarvis.runtime.state import AgentState
from jarvis.schemas import ChatMessage


class LLMDecisionProvider:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def decide(self, state: AgentState, tools: list[dict[str, Any]]) -> dict[str, Any]:
        observations = state.observations[-8:]
        system = """You are the JARVIS-X runtime controller. Decide the next safe action.
Return JSON only. Either:
{"type":"tool","tool":"name","args":{...}}
or {"type":"final","answer":"..."}.
Use only listed tools. Never claim an action succeeded before observing its result.
Prefer a final answer when the goal is satisfied. Avoid repeating actions."""
        content = f"Goal: {state.goal}\nTools: {tools}\nRecent observations: {observations}"
        messages = [ChatMessage(role="user", content=content)]
        raw = await self.provider.chat(messages, system=system)
        data = extract_json_object(raw)
        if not data:
            return {"type": "final", "answer": raw}
        if data.get("type") == "tool" and data.get("tool"):
            return {"type": "tool", "tool": str(data["tool"]), "args": dict(data.get("args") or {})}
        return {"type": "final", "answer": str(data.get("answer") or data.get("final") or raw)}
