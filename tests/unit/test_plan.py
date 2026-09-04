import pytest

from jarvis.runtime.plan import Plan, PlanStep


def test_plan_dependency_validation_and_ready_step():
    first = PlanStep("research")
    second = PlanStep("write", depends_on=[first.id])
    plan = Plan("report", [first, second])
    plan.validate()
    assert plan.next_ready() is first


def test_plan_rejects_cycle():
    a = PlanStep("a")
    b = PlanStep("b")
    a.depends_on = [b.id]
    b.depends_on = [a.id]
    with pytest.raises(ValueError, match="cycle"):
        Plan("x", [a, b]).validate()
