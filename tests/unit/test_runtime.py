import pytest

from jarvis.runtime.engine import AgentRuntime
from jarvis.runtime.state import AgentState, Budget, RunStatus


class FakeDecision:
    def __init__(self):
        self.calls = 0

    async def decide(self, state, tools):
        self.calls += 1
        if self.calls == 1:
            return {"type": "tool", "tool": "calculator", "args": {"expression": "2+2"}}
        return {"type": "final", "answer": "4"}


@pytest.mark.asyncio
async def test_runtime_reason_act_observe():
    async def runner(name, args):
        return {"output": "4"}

    async def approval(name, args):
        return True

    state = AgentState(
        "calculate",
        "s1",
        budget=Budget(max_steps=4, max_tool_calls=3, max_elapsed_seconds=10, max_prompt_chars=10000),
    )
    runtime = AgentRuntime(FakeDecision(), runner, approval, [{"name": "calculator"}])
    result = await runtime.run(state)
    assert result.status == RunStatus.COMPLETED
    assert result.final_answer == "4"
    assert result.budget.tool_calls == 1
    assert result.observations[0]["result"]["output"] == "4"
