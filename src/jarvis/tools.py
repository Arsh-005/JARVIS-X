import ast
import math
import operator
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from jarvis.audit import audit
from jarvis.config import get_settings
from jarvis.db import Database

ToolFunc = Callable[[dict[str, Any], str], Awaitable[str]]


@dataclass
class ToolSpec:
    name: str
    description: str
    writes: bool
    func: ToolFunc


class ConfirmationStore:
    def __init__(self) -> None:
        self._tokens: dict[str, tuple[str, dict[str, Any]]] = {}

    def issue(self, tool_name: str, args: dict[str, Any]) -> str:
        token = secrets.token_urlsafe(16)
        self._tokens[token] = (tool_name, args)
        return token

    def consume(self, token: str, tool_name: str, args: dict[str, Any]) -> bool:
        item = self._tokens.pop(token, None)
        return item == (tool_name, args)


confirmations = ConfirmationStore()


def safe_path(relative: str) -> Path:
    root = get_settings().workspace_dir.resolve()
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("Path escapes the configured workspace")
    return candidate


_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def eval_math(expr: str) -> float:
    def walk(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
            return _ALLOWED_BINOPS[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY:
            return _ALLOWED_UNARY[type(node.op)](walk(node.operand))
        raise ValueError("Unsupported expression")

    value = walk(ast.parse(expr, mode="eval"))
    if not math.isfinite(value):
        raise ValueError("Result is not finite")
    return value


async def tool_calculator(args: dict[str, Any], session_id: str) -> str:
    return str(eval_math(str(args.get("expression", ""))))


async def tool_time(args: dict[str, Any], session_id: str) -> str:
    return datetime.now(UTC).isoformat()


async def tool_remember(args: dict[str, Any], session_id: str) -> str:
    content = str(args.get("content", "")).strip()
    if not content:
        raise ValueError("content is required")
    Database().add_memory(session_id, str(args.get("kind", "note")), content)
    return "Memory stored."


async def tool_read_file(args: dict[str, Any], session_id: str) -> str:
    path = safe_path(str(args.get("path", "")))
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")[:20000]


async def tool_write_file(args: dict[str, Any], session_id: str) -> str:
    path = safe_path(str(args.get("path", "")))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(args.get("content", "")), encoding="utf-8")
    return f"Wrote {path.relative_to(get_settings().workspace_dir.resolve())}"


async def tool_web_fetch(args: dict[str, Any], session_id: str) -> str:
    settings = get_settings()
    if not settings.allow_web_fetch:
        raise PermissionError("Web fetch is disabled")
    url = str(args.get("url", ""))
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only http/https URLs are supported")
    if settings.allowed_hosts and parsed.hostname.lower() not in settings.allowed_hosts:
        raise PermissionError("Host is not in WEB_FETCH_ALLOWED_HOSTS")
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        response = await client.get(url, headers={"User-Agent": "JARVIS-X/1.0"})
    response.raise_for_status()
    ctype = response.headers.get("content-type", "")
    if not any(x in ctype for x in ("text/", "application/json", "application/xml")):
        raise ValueError("Refusing non-text response")
    return response.text[:20000]


async def tool_computer(args: dict[str, Any], session_id: str) -> str:
    settings = get_settings()
    if not settings.enable_local_computer_tools:
        raise PermissionError("Local computer tools are disabled")
    try:
        import pyautogui  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Install optional dependency: pip install -e '.[local]'") from exc
    action = str(args.get("action", ""))
    if action == "move":
        pyautogui.moveTo(int(args["x"]), int(args["y"]), duration=0.2)
    elif action == "click":
        pyautogui.click(int(args["x"]), int(args["y"]))
    elif action == "type":
        pyautogui.write(str(args.get("text", "")), interval=0.02)
    elif action == "press":
        key = str(args.get("key", ""))
        if key not in {"enter", "tab", "esc", "space", "up", "down", "left", "right"}:
            raise ValueError("Key is not in the safe allowlist")
        pyautogui.press(key)
    else:
        raise ValueError("Allowed computer actions: move, click, type, press")
    return f"Computer action {action} executed."


TOOLS: dict[str, ToolSpec] = {
    "calculator": ToolSpec(
        "calculator", "Evaluate arithmetic. args: {expression:string}", False, tool_calculator
    ),
    "current_time": ToolSpec("current_time", "Return current UTC timestamp. args:{}", False, tool_time),
    "remember": ToolSpec(
        "remember",
        "Store persistent session memory. args:{content:string, kind?:string}",
        True,
        tool_remember,
    ),
    "read_file": ToolSpec(
        "read_file", "Read UTF-8 file inside workspace. args:{path:string}", False, tool_read_file
    ),
    "write_file": ToolSpec(
        "write_file",
        "Write UTF-8 file inside workspace. args:{path:string, content:string}",
        True,
        tool_write_file,
    ),
    "web_fetch": ToolSpec("web_fetch", "Fetch a public text URL. args:{url:string}", False, tool_web_fetch),
    "computer": ToolSpec(
        "computer",
        "Optional constrained local mouse/keyboard control. args:{action:move|click|type|press,...}",
        True,
        tool_computer,
    ),
}


def tools_description() -> str:
    return "\n".join(f"- {t.name}: {t.description}; writes={t.writes}" for t in TOOLS.values())


async def execute_tool(
    name: str, args: dict[str, Any], session_id: str, confirm_token: str | None = None
) -> tuple[str, str | None]:
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")
    spec = TOOLS[name]
    settings = get_settings()
    if spec.writes and settings.require_confirmation_for_writes:
        if not confirm_token or not confirmations.consume(confirm_token, name, args):
            token = confirmations.issue(name, args)
            audit("tool_confirmation_required", {"session_id": session_id, "tool": name, "args": args})
            return f"Confirmation required before executing write-capable tool '{name}'.", token
    audit("tool_started", {"session_id": session_id, "tool": name, "args": args})
    try:
        result = await spec.func(args, session_id)
    except Exception as exc:
        audit("tool_failed", {"session_id": session_id, "tool": name, "error": str(exc)})
        raise
    audit("tool_completed", {"session_id": session_id, "tool": name})
    return result, None
