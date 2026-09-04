from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any


class RiskLevel(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass(frozen=True, slots=True)
class ToolPolicy:
    risk: RiskLevel
    requires_confirmation: bool = False
    enabled_by_default: bool = True


DEFAULT_POLICIES: dict[str, ToolPolicy] = {
    "calculator": ToolPolicy(RiskLevel.LOW),
    "time": ToolPolicy(RiskLevel.LOW),
    "memory_search": ToolPolicy(RiskLevel.LOW),
    "rag_search": ToolPolicy(RiskLevel.LOW),
    "web_fetch": ToolPolicy(RiskLevel.MEDIUM),
    "workspace_read": ToolPolicy(RiskLevel.MEDIUM),
    "workspace_write": ToolPolicy(RiskLevel.HIGH, True),
    "computer_action": ToolPolicy(RiskLevel.CRITICAL, True, False),
}


class PolicyEngine:
    def __init__(self, policies: dict[str, ToolPolicy] | None = None) -> None:
        self.policies = policies or DEFAULT_POLICIES

    def evaluate(self, tool: str, args: dict[str, Any], confirmed: bool = False) -> tuple[bool, str]:
        policy = self.policies.get(tool, ToolPolicy(RiskLevel.HIGH, True, False))
        if not policy.enabled_by_default:
            return False, "tool disabled by default"
        if policy.requires_confirmation and not confirmed:
            return False, "human confirmation required"
        if any(str(v).startswith(("/etc/", "C:\\Windows", "/root/")) for v in args.values()):
            return False, "protected system path"
        return True, "allowed"
