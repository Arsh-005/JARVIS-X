from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: str | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    use_rag: bool = True


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    provider: str
    sources: list[dict[str, Any]] = []
    latency_ms: int


class AgentRequest(ChatRequest):
    confirm_token: str | None = None


class AgentStep(BaseModel):
    index: int
    thought: str
    action: str | None = None
    action_input: dict[str, Any] = {}
    observation: str | None = None


class AgentResponse(BaseModel):
    session_id: str
    answer: str
    status: Literal["completed", "needs_confirmation", "stopped"]
    steps: list[AgentStep]
    provider: str
    latency_ms: int
    confirmation_token: str | None = None


class IngestRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=500000)
    source: str = "manual"


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = {}


class VisionRequest(BaseModel):
    image_base64: str
    prompt: str = "Describe this image and highlight anything relevant to the user's task."


class MultiAgentRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=20000)
    session_id: str = Field(default_factory=lambda: str(uuid4()))
