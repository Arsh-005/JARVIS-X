import asyncio
import base64
import json
import random
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from jarvis.config import Settings, get_settings
from jarvis.schemas import ChatMessage, ToolCall


class LLMError(RuntimeError):
    pass


class LLMProvider(ABC):
    name = "base"

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        system: str = "",
    ) -> str:
        """Return a safe local response for providers without a backend.

        Concrete providers override this method with their API-specific
        implementation, while the default keeps the base class usable for
        lightweight or test providers.
        """
        last = messages[-1].content if messages else ""

        return (
            "No remote language model is configured for this provider. "
            f"I received: {last}"
        )

    async def vision(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
    ) -> str:
        raise LLMError(
            f"Vision is not supported by provider {self.name}"
        )


class LocalProvider(LLMProvider):
    name = "local"

    async def chat(
        self,
        messages: list[ChatMessage],
        system: str = "",
    ) -> str:
        last = messages[-1].content if messages else ""

        return (
            "JARVIS-X is running in local fallback mode, "
            "so no external LLM is configured. "
            f"I received: {last}\n\n"
            "Add OPENAI_API_KEY or GEMINI_API_KEY in .env "
            "for model reasoning."
        )


class OpenAIProvider(LLMProvider):
    """
    OpenAI-compatible provider.

    In the current JARVIS-X architecture this is also used
    for OmniRoute because OmniRoute exposes an OpenAI-style API.

    TEXT:
        JARVIS-X -> OmniRoute -> routed provider/model

    VISION:
        JARVIS-X -> GeminiProvider -> Google Gemini directly
    """

    name = "openai"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def chat(
        self,
        messages: list[ChatMessage],
        system: str = "",
    ) -> str:
        payload_messages: list[dict[str, Any]] = []

        if system:
            payload_messages.append(
                {
                    "role": "system",
                    "content": system,
                }
            )

        payload_messages.extend(
            {
                "role": message.role,
                "content": message.content,
            }
            for message in messages
            if message.role != "tool"
        )

        payload = {
            "model": self.settings.openai_model,
            "messages": payload_messages,
            "temperature": self.settings.llm_temperature,
            "stream": False,
        }

        headers = {
            "Authorization": (
                f"Bearer {self.settings.openai_api_key}"
            ),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        url = (
            f"{self.settings.openai_base_url.rstrip('/')}"
            "/chat/completions"
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.settings.llm_timeout_seconds
            ) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )

        except httpx.TimeoutException as exc:
            raise LLMError(
                "OpenAI-compatible provider timed out."
            ) from exc

        except httpx.ConnectError as exc:
            raise LLMError(
                "Could not connect to the OpenAI-compatible "
                "provider. If you are using OmniRoute locally, "
                "make sure OmniRoute is running."
            ) from exc

        except httpx.HTTPError as exc:
            raise LLMError(
                f"OpenAI-compatible HTTP error: {exc}"
            ) from exc

        if response.is_error:
            raise LLMError(
                "OpenAI-compatible API error "
                f"{response.status_code}: "
                f"{response.text[:1000]}"
            )

        content_type = (
            response.headers
            .get("content-type", "")
            .lower()
        )

        # -------------------------------------------------
        # Normal JSON response
        # -------------------------------------------------

        if "application/json" in content_type:
            try:
                data = response.json()

            except ValueError as exc:
                raise LLMError(
                    "Provider returned invalid JSON: "
                    f"{response.text[:1000]}"
                ) from exc

            try:
                content = (
                    data["choices"][0]["message"]["content"]
                )

            except (
                KeyError,
                IndexError,
                TypeError,
            ) as exc:
                raise LLMError(
                    f"Unexpected provider response: {data}"
                ) from exc

            if isinstance(content, str):
                return content

            if isinstance(content, list):
                pieces: list[str] = []

                for item in content:
                    if not isinstance(item, dict):
                        continue

                    if item.get("type") == "text":
                        text = item.get("text")

                        if isinstance(text, str):
                            pieces.append(text)

                if pieces:
                    return "\n".join(pieces)

            raise LLMError(
                "Provider returned no usable assistant text."
            )

        # -------------------------------------------------
        # SSE compatibility
        # -------------------------------------------------
        #
        # Some OpenAI-compatible gateways return SSE even
        # when stream=False.
        # -------------------------------------------------

        if (
            "text/event-stream" in content_type
            or response.text.startswith("data:")
        ):
            pieces: list[str] = []

            for line in response.text.splitlines():
                line = line.strip()

                if not line.startswith("data:"):
                    continue

                raw = line[5:].strip()

                if not raw or raw == "[DONE]":
                    continue

                try:
                    chunk = json.loads(raw)

                except json.JSONDecodeError:
                    continue

                choices = chunk.get("choices", [])

                if not choices:
                    continue

                choice = choices[0]

                delta = choice.get("delta", {})
                piece = delta.get("content")

                if piece:
                    pieces.append(piece)
                    continue

                message = choice.get("message", {})
                piece = message.get("content")

                if piece:
                    pieces.append(piece)

            answer = "".join(pieces).strip()

            if answer:
                return answer

            raise LLMError(
                "Provider returned an SSE response but "
                "no assistant text was found."
            )

        raise LLMError(
            "Provider returned an unsupported response format. "
            f"HTTP {response.status_code}, "
            f"Content-Type={content_type!r}, "
            f"Body={response.text[:1000]!r}"
        )

    async def openai_compatible(
        self,
        messages: list[ChatMessage],
        system: str = "",
    ) -> str:
        """
        Compatibility helper retained for other JARVIS-X
        components that may call it directly.
        """

        payload_messages: list[dict[str, Any]] = []

        if system:
            payload_messages.append(
                {
                    "role": "system",
                    "content": system,
                }
            )

        payload_messages.extend(
            {
                "role": message.role,
                "content": message.content,
            }
            for message in messages
            if message.role != "tool"
        )

        payload = {
            "model": self.settings.openai_model,
            "messages": payload_messages,
            "temperature": self.settings.llm_temperature,
            "stream": False,
        }

        headers = {
            "Authorization": (
                f"Bearer {self.settings.openai_api_key}"
            ),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        url = (
            f"{self.settings.openai_base_url.rstrip('/')}"
            "/chat/completions"
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.settings.llm_timeout_seconds
            ) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )

        except httpx.TimeoutException as exc:
            raise LLMError(
                "OpenAI-compatible provider timed out."
            ) from exc

        except httpx.ConnectError as exc:
            raise LLMError(
                "Could not connect to the OpenAI-compatible "
                "provider."
            ) from exc

        except httpx.HTTPError as exc:
            raise LLMError(
                f"OpenAI-compatible HTTP error: {exc}"
            ) from exc

        if response.is_error:
            raise LLMError(
                "OpenAI-compatible error "
                f"{response.status_code}: "
                f"{response.text[:1000]}"
            )

        try:
            data = response.json()

        except ValueError as exc:
            raise LLMError(
                "OpenAI-compatible provider returned "
                "invalid JSON."
            ) from exc

        try:
            return data["choices"][0]["message"]["content"]

        except (
            KeyError,
            IndexError,
            TypeError,
        ) as exc:
            raise LLMError(
                f"Unexpected provider response: {data}"
            ) from exc

    async def vision(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
    ) -> str:
        """
        Route image understanding directly to Gemini.

        Normal text/reasoning remains routed through the
        OpenAI-compatible provider such as OmniRoute.

        This avoids OmniRoute vision queue/cooldown issues while
        preserving OmniRoute for normal text routing.
        """

        if not self.settings.gemini_api_key:
            raise LLMError(
                "Vision is configured to use Gemini directly, "
                "but GEMINI_API_KEY is missing. Add your Google "
                "AI Studio API key to the JARVIS-X .env file."
            )

        gemini = GeminiProvider(self.settings)

        return await gemini.vision(
            image_bytes=image_bytes,
            mime_type=mime_type,
            prompt=prompt,
        )


class GeminiProvider(LLMProvider):
    """
    Native Google Gemini provider.

    Used directly for vision and optionally for normal chat when
    LLM_PROVIDER=gemini.
    """

    name = "gemini"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def chat(
        self,
        messages: list[ChatMessage],
        system: str = "",
    ) -> str:
        contents: list[dict[str, Any]] = []

        for message in messages:
            if message.role in {"system", "tool"}:
                continue

            role = "model" if message.role == "assistant" else "user"

            contents.append(
                {
                    "role": role,
                    "parts": [{"text": message.content}],
                }
            )

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.settings.llm_temperature,
            },
        }

        if system:
            payload["systemInstruction"] = {
                "parts": [{"text": system}],
            }

        # Primary model comes from GEMINI_MODEL.
        # Stable fallback models are tried if the primary model
        # remains temporarily unavailable.
        models = [
            self.settings.gemini_model,
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
        ]

        # Remove duplicates while preserving order.
        models = list(dict.fromkeys(models))

        retryable_statuses = {408, 429, 500, 502, 503, 504}

        errors: list[str] = []

        async with httpx.AsyncClient(
            timeout=self.settings.llm_timeout_seconds
        ) as client:
            for model in models:
                url = (
                    "https://generativelanguage.googleapis.com/"
                    f"v1beta/models/{model}:generateContent"
                    f"?key={self.settings.gemini_api_key}"
                )

                # Three attempts for each model.
                for attempt in range(3):
                    try:
                        response = await client.post(
                            url,
                            json=payload,
                        )

                    except httpx.TimeoutException:
                        errors.append(
                            f"{model}: timeout on attempt {attempt + 1}"
                        )

                        if attempt < 2:
                            delay = (2**attempt) + random.uniform(0, 0.5)
                            await asyncio.sleep(delay)
                            continue

                        break

                    except httpx.ConnectError:
                        errors.append(
                            f"{model}: connection error on "
                            f"attempt {attempt + 1}"
                        )

                        if attempt < 2:
                            delay = (2**attempt) + random.uniform(0, 0.5)
                            await asyncio.sleep(delay)
                            continue

                        break

                    except httpx.HTTPError as exc:
                        errors.append(
                            f"{model}: HTTP client error: {exc}"
                        )
                        break

                    if response.is_error:
                        status = response.status_code

                        errors.append(
                            f"{model}: HTTP {status}"
                        )

                        if status in retryable_statuses:
                            if attempt < 2:
                                delay = (
                                    (2**attempt)
                                    + random.uniform(0, 0.5)
                                )
                                await asyncio.sleep(delay)
                                continue

                            # This model remained unavailable.
                            # Move to the next fallback model.
                            break

                        # 400/401/403 etc. normally indicate a
                        # configuration/request problem. Do not
                        # repeatedly hammer the API.
                        raise LLMError(
                            f"Gemini request failed with HTTP {status}: "
                            f"{response.text[:500]}"
                        )

                    try:
                        data = response.json()

                    except ValueError:
                        errors.append(
                            f"{model}: invalid JSON response"
                        )
                        break

                    try:
                        candidates = data["candidates"]

                        if not candidates:
                            errors.append(
                                f"{model}: no candidates returned"
                            )
                            break

                        parts = candidates[0]["content"]["parts"]

                        text_parts = [
                            part["text"]
                            for part in parts
                            if isinstance(part, dict)
                            and isinstance(part.get("text"), str)
                            and part["text"].strip()
                        ]

                        if text_parts:
                            return "\n".join(text_parts)

                        errors.append(
                            f"{model}: response contained no text"
                        )
                        break

                    except (
                        KeyError,
                        IndexError,
                        TypeError,
                    ):
                        errors.append(
                            f"{model}: unexpected response structure"
                        )
                        break

        summary = "; ".join(errors[-10:])

        raise LLMError(
            "JARVIS-X could not reach an available Gemini model "
            "after automatic retries and model fallback. "
            "Please try again shortly. "
            f"Attempts: {summary}"
        )
    async def vision(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
    ) -> str:
        """
        Native Gemini multimodal image understanding.

        Sends:
            user text
            +
            inline base64 image

        directly to the Google Gemini generateContent API.
        """

        if not self.settings.gemini_api_key:
            raise LLMError(
                "GEMINI_API_KEY is missing."
            )

        if not image_bytes:
            raise LLMError(
                "The uploaded image is empty."
            )

        if not mime_type.startswith("image/"):
            raise LLMError(
                "Gemini vision received an unsupported MIME "
                f"type: {mime_type}"
            )

        encoded_image = (
            base64.b64encode(image_bytes).decode("utf-8")
        )

        payload: dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": prompt,
                        },
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": encoded_image,
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {
                "temperature": (
                    self.settings.llm_temperature
                )
            },
        }

        model = self.settings.gemini_model

        url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models/{model}:generateContent"
            f"?key={self.settings.gemini_api_key}"
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.settings.llm_timeout_seconds
            ) as client:
                response = await client.post(
                    url,
                    json=payload,
                )

        except httpx.TimeoutException as exc:
            raise LLMError(
                "Gemini vision request timed out."
            ) from exc

        except httpx.ConnectError as exc:
            raise LLMError(
                "Could not connect to Google Gemini for vision."
            ) from exc

        except httpx.HTTPError as exc:
            raise LLMError(
                f"Gemini vision HTTP error: {exc}"
            ) from exc

        if response.is_error:
            raise LLMError(
                "Gemini vision error "
                f"{response.status_code}: "
                f"{response.text[:1500]}"
            )

        try:
            data = response.json()

        except ValueError as exc:
            raise LLMError(
                "Gemini vision returned invalid JSON."
            ) from exc

        try:
            candidates = data["candidates"]

            if not candidates:
                raise LLMError(
                    f"Gemini returned no candidates: {data}"
                )

            parts = candidates[0]["content"]["parts"]

            text_parts: list[str] = []

            for part in parts:
                if not isinstance(part, dict):
                    continue

                text = part.get("text")

                if isinstance(text, str) and text.strip():
                    text_parts.append(text.strip())

            if text_parts:
                return "\n".join(text_parts)

        except LLMError:
            raise

        except (
            KeyError,
            IndexError,
            TypeError,
        ) as exc:
            raise LLMError(
                f"Unexpected Gemini vision response: {data}"
            ) from exc

        raise LLMError(
            "Gemini vision returned no usable text."
        )


class ProviderRouter:
    def __init__(
        self,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()

    def get(self) -> LLMProvider:
        choice = self.settings.llm_provider

        if (
            choice == "openai"
            and self.settings.openai_api_key
        ):
            return OpenAIProvider(self.settings)

        if (
            choice == "gemini"
            and self.settings.gemini_api_key
        ):
            return GeminiProvider(self.settings)

        if choice == "local":
            return LocalProvider()

        # Auto-style fallback:
        # prefer the OpenAI-compatible provider first because
        # this is where OmniRoute is normally configured.
        if self.settings.openai_api_key:
            return OpenAIProvider(self.settings)

        if self.settings.gemini_api_key:
            return GeminiProvider(self.settings)

        return LocalProvider()


def extract_json_object(
    text: str,
) -> dict[str, Any] | None:
    text = text.strip()

    if text.startswith("```"):
        text = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            text,
            flags=re.S,
        )

    try:
        data = json.loads(text)

        return data if isinstance(data, dict) else None

    except json.JSONDecodeError:
        match = re.search(
            r"\{.*\}",
            text,
            re.S,
        )

        if not match:
            return None

        try:
            data = json.loads(match.group(0))

            return (
                data
                if isinstance(data, dict)
                else None
            )

        except json.JSONDecodeError:
            return None


async def ask_for_tool_call(
    provider: LLMProvider,
    messages: list[ChatMessage],
    tools_description: str,
) -> tuple[str, ToolCall | None]:
    system = f"""
You are JARVIS-X, a careful AI agent.

You can either answer the user directly or request ONE tool.

Available tools:

{tools_description}

When a tool is needed, output ONLY JSON in this exact shape:

{{
    "thought": "brief reason",
    "action": "tool_name",
    "arguments": {{}}
}}

When no tool is needed, output ONLY JSON:

{{
    "thought": "brief reason",
    "final": "answer to user"
}}

Rules:
- Never invent a tool.
- Never claim a tool succeeded before seeing its observation.
- Request only one tool at a time.
- Use the final field when no tool is required.
""".strip()

    raw = await provider.chat(
        messages,
        system=system,
    )

    data = extract_json_object(raw)

    if not data:
        return raw, None

    if data.get("action"):
        return (
            str(data.get("thought", "")),
            ToolCall(
                name=str(data["action"]),
                arguments=(
                    data.get("arguments") or {}
                ),
            ),
        )

    return (
        str(data.get("final") or raw),
        None,
    )