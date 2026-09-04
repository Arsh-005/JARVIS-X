import httpx

from jarvis.config import get_settings
from jarvis.llm import LLMError


async def transcribe_audio(filename: str, audio: bytes, content_type: str) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise LLMError("Speech-to-text requires OPENAI_API_KEY")
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    files = {"file": (filename, audio, content_type)}
    data = {"model": "gpt-4o-mini-transcribe"}
    async with httpx.AsyncClient(timeout=max(60, settings.llm_timeout_seconds)) as client:
        response = await client.post(
            "https://api.openai.com/v1/audio/transcriptions", headers=headers, files=files, data=data
        )
    if response.is_error:
        raise LLMError(f"Speech-to-text error {response.status_code}: {response.text[:500]}")
    return response.json()["text"]


async def synthesize_speech(text: str, voice: str = "alloy") -> bytes:
    settings = get_settings()
    if not settings.openai_api_key:
        raise LLMError("Text-to-speech requires OPENAI_API_KEY")
    payload = {"model": "gpt-4o-mini-tts", "voice": voice, "input": text, "format": "mp3"}
    headers = {"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=max(60, settings.llm_timeout_seconds)) as client:
        response = await client.post("https://api.openai.com/v1/audio/speech", headers=headers, json=payload)
    if response.is_error:
        raise LLMError(f"Text-to-speech error {response.status_code}: {response.text[:500]}")
    return response.content
