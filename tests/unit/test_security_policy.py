from jarvis.security.policy import PolicyEngine


def test_write_needs_confirmation():
    allowed, reason = PolicyEngine().evaluate("workspace_write", {"path": "notes.txt"}, confirmed=False)
    assert not allowed and "confirmation" in reason


def test_low_risk_tool_allowed():
    allowed, _ = PolicyEngine().evaluate("calculator", {}, confirmed=False)
    assert allowed
