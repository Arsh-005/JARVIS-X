from time import perf_counter

from jarvis.audit import audit
from jarvis.config import get_settings
from jarvis.db import Database
from jarvis.llm import ProviderRouter, ask_for_tool_call
from jarvis.rag import RAGStore
from jarvis.schemas import AgentResponse, AgentStep, ChatMessage, ChatResponse
from jarvis.tools import execute_tool, tools_description

SYSTEM_PROMPT = """You are JARVIS-X, a concise, capable AI engineering assistant.
Use supplied memory and retrieved context when relevant. Distinguish retrieved facts from your own reasoning.
Never pretend that an action, lookup, write, or external operation occurred unless an observation confirms it.
If context is insufficient, say so rather than fabricating details."""


class AssistantService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.db = Database()
        self.rag = RAGStore(self.db)
        self.provider = ProviderRouter().get()

    def _history(self, session_id: str) -> list[ChatMessage]:
        return [ChatMessage(role=m["role"], content=m["content"]) for m in self.db.get_messages(session_id)]

    def _context(self, session_id: str, query: str, use_rag: bool) -> tuple[str, list[dict]]:
        memories = self.db.get_memories(session_id, limit=8)
        sources = self.rag.search(query, limit=5) if use_rag else []
        parts = []
        if memories:
            parts.append(
                "Persistent memory:\n" + "\n".join(f"- [{m['kind']}] {m['content']}" for m in memories)
            )
        if sources:
            parts.append(
                "Retrieved knowledge:\n"
                + "\n\n".join(
                    f"[{i + 1}] {s['title']} ({s['source']})\n{s['content']}" for i, s in enumerate(sources)
                )
            )
        return "\n\n".join(parts)[: self.settings.max_context_chars], sources

    async def chat(self, session_id: str, message: str, use_rag: bool = True) -> ChatResponse:
        start = perf_counter()
        context, sources = self._context(session_id, message, use_rag)
        history = self._history(session_id)
        self.db.add_message(session_id, "user", message)
        user_content = message if not context else f"{message}\n\nCONTEXT:\n{context}"
        messages = history + [ChatMessage(role="user", content=user_content)]
        answer = await self.provider.chat(messages, system=SYSTEM_PROMPT)
        self.db.add_message(session_id, "assistant", answer)
        latency = int((perf_counter() - start) * 1000)
        audit(
            "chat_completed",
            {"session_id": session_id, "provider": self.provider.name, "latency_ms": latency},
        )
        return ChatResponse(
            session_id=session_id,
            answer=answer,
            provider=self.provider.name,
            sources=[
                {k: s[k] for k in ("score", "title", "source", "document_id", "chunk_index")} for s in sources
            ],
            latency_ms=latency,
        )

    async def run_agent(
        self, session_id: str, message: str, use_rag: bool = True, confirm_token: str | None = None
    ) -> AgentResponse:
        start = perf_counter()
        context, _ = self._context(session_id, message, use_rag)
        self.db.add_message(session_id, "user", message)
        messages = self._history(session_id)
        if context:
            messages.append(ChatMessage(role="system", content="Relevant context:\n" + context))
        steps: list[AgentStep] = []
        tool_calls = 0
        pending_confirm = confirm_token
        for index in range(1, self.settings.max_agent_steps + 1):
            output, tool_call = await ask_for_tool_call(self.provider, messages, tools_description())
            if tool_call is None:
                answer = output
                self.db.add_message(session_id, "assistant", answer)
                return AgentResponse(
                    session_id=session_id,
                    answer=answer,
                    status="completed",
                    steps=steps + [AgentStep(index=index, thought="Final response")],
                    provider=self.provider.name,
                    latency_ms=int((perf_counter() - start) * 1000),
                )
            tool_calls += 1
            if tool_calls > self.settings.max_tool_calls:
                break
            step = AgentStep(
                index=index, thought=output, action=tool_call.name, action_input=tool_call.arguments
            )
            try:
                observation, token = await execute_tool(
                    tool_call.name, tool_call.arguments, session_id, pending_confirm
                )
                pending_confirm = None
            except Exception as exc:
                observation, token = f"Tool error: {exc}", None
            step.observation = observation
            steps.append(step)
            if token:
                return AgentResponse(
                    session_id=session_id,
                    answer=observation,
                    status="needs_confirmation",
                    steps=steps,
                    provider=self.provider.name,
                    latency_ms=int((perf_counter() - start) * 1000),
                    confirmation_token=token,
                )
            messages.append(
                ChatMessage(
                    role="assistant",
                    content=f"Thought: {output}\nAction: {tool_call.name}\nArguments: {tool_call.arguments}",
                )
            )
            messages.append(ChatMessage(role="tool", name=tool_call.name, content=observation))
            messages.append(
                ChatMessage(
                    role="user",
                    content=f"Tool observation for {tool_call.name}: {observation}\nContinue toward the original goal.",
                )
            )
        answer = "Agent stopped because the configured step/tool budget was exhausted."
        self.db.add_message(session_id, "assistant", answer)
        return AgentResponse(
            session_id=session_id,
            answer=answer,
            status="stopped",
            steps=steps,
            provider=self.provider.name,
            latency_ms=int((perf_counter() - start) * 1000),
        )
