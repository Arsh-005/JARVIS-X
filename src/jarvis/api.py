import base64
import mimetypes
import time
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from jarvis.attachments import save_upload
from jarvis.auth.api_keys import require_api_key
from jarvis.cache.ttl import TTLCache
from jarvis.config import get_settings
from jarvis.db import Database
from jarvis.infrastructure.rate_limit import TokenBucket
from jarvis.llm import LLMError, ProviderRouter
from jarvis.logging_setup import configure_logging
from jarvis.memory.manager import MemoryManager
from jarvis.memory.models import MemoryKind, MemoryRecord
from jarvis.multi_agent import run_review_workflow
from jarvis.observability.metrics import metrics
from jarvis.rag import RAGStore
from jarvis.runtime.service import RuntimeService
from jarvis.schemas import AgentRequest, ChatRequest, IngestRequest, MultiAgentRequest, VisionRequest
from jarvis.services import AssistantService
from jarvis.speech import synthesize_speech, transcribe_audio

configure_logging()
settings = get_settings()
app = FastAPI(
    title="JARVIS-X Ultimate", version="2.0.0", description="Production-style multimodal agentic AI assistant"
)
response_cache = TTLCache(max_items=256, ttl_seconds=180)
request_bucket = TokenBucket(
    rate_per_second=settings.rate_limit_per_minute / 60.0, capacity=float(settings.rate_limit_per_minute)
)
static_dir = Path(__file__).resolve().parents[2] / "static"
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.middleware("http")
async def request_metadata(request: Request, call_next):
    if request.url.path.startswith("/api/") and not request_bucket.allow():
        return Response(content="rate limit exceeded", status_code=429, media_type="text/plain")
    request_id = request.headers.get("x-request-id", str(uuid4()))
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    response.headers["x-process-time-ms"] = str(int((time.perf_counter() - start) * 1000))
    return response


@app.get("/")
async def home():
    return FileResponse(static_dir / "index.html")


@app.get("/health")
async def health():
    provider = ProviderRouter().get()
    return {
        "status": "ok",
        "app": settings.app_name,
        "provider": provider.name,
        "environment": settings.app_env,
    }


@app.get("/ready")
async def ready():
    provider = ProviderRouter().get()
    return {"status": "ready", "provider": provider.name, "environment": settings.app_env}


@app.get("/metrics")
async def prometheus_metrics():
    if not settings.enable_prometheus:
        raise HTTPException(status_code=404, detail="metrics disabled")
    try:
        from jarvis.observability.prometheus import build_metrics_response

        payload, content_type = build_metrics_response()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return Response(content=payload, media_type=content_type)


@app.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        return await AssistantService().chat(req.session_id, req.message, req.use_rag)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/agent/run")
async def run_agent(req: AgentRequest):
    try:
        return await AssistantService().run_agent(req.session_id, req.message, req.use_rag, req.confirm_token)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/agents/review")
async def agent_review(req: MultiAgentRequest):
    return await run_review_workflow(req.goal)


@app.post("/api/documents/ingest")
async def ingest(req: IngestRequest):
    return RAGStore().ingest(req.title, req.text, req.source)


@app.post("/api/attachments/upload")
async def attachment_upload(
    file: Annotated[UploadFile, File()],
):
    """Store a UI attachment and extract text when the format supports it."""
    result = await save_upload(file)
    text = str(result.get("text", "")).strip()
    if text:
        rag_result = RAGStore().ingest(result["filename"], text, "attachment")
        result["document_id"] = rag_result["document_id"]
        result["chunks"] = rag_result["chunks"]
    result.pop("text", None)
    return result


@app.post("/api/documents/upload")
async def upload(
    file: Annotated[UploadFile, File()],
):
    allowed = {".txt", ".md", ".json", ".csv"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail=f"Supported extensions: {sorted(allowed)}")
    raw = await file.read()
    if len(raw) > 5_000_000:
        raise HTTPException(status_code=413, detail="File is larger than 5 MB")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="File must be UTF-8 text") from exc
    return RAGStore().ingest(file.filename or "upload", text, "upload")


@app.get("/api/search")
async def search(q: str = Query(min_length=1), limit: int = Query(default=5, ge=1, le=20)):
    return {"query": q, "results": RAGStore().search(q, limit)}


@app.get("/api/sessions/{session_id}")
async def session(session_id: str):
    db = Database()
    return {
        "session_id": session_id,
        "messages": db.get_messages(session_id, 100),
        "memories": db.get_memories(session_id, 100),
    }


@app.post("/api/vision/analyze")
async def vision(req: VisionRequest):
    try:
        image = base64.b64decode(req.image_base64, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 image") from exc
    if len(image) > 8_000_000:
        raise HTTPException(status_code=413, detail="Image larger than 8 MB")
    provider = ProviderRouter().get()
    try:
        answer = await provider.vision(image, "image/jpeg", req.prompt)
    except LLMError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"provider": provider.name, "answer": answer}


@app.post("/api/vision/upload")
async def vision_upload(
    file: Annotated[UploadFile, File()],
    prompt: str = "Describe this image and highlight important details.",
):
    raw = await file.read()
    if len(raw) > 8_000_000:
        raise HTTPException(status_code=413, detail="Image larger than 8 MB")
    mime = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "image/jpeg"
    provider = ProviderRouter().get()
    try:
        answer = await provider.vision(raw, mime, prompt)
    except LLMError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"provider": provider.name, "answer": answer}


@app.post("/api/speech/transcribe")
async def speech_transcribe(
    file: Annotated[UploadFile, File()],
):
    raw = await file.read()
    if len(raw) > 20_000_000:
        raise HTTPException(status_code=413, detail="Audio larger than 20 MB")
    try:
        text = await transcribe_audio(file.filename or "audio.webm", raw, file.content_type or "audio/webm")
    except LLMError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"text": text}


@app.post("/api/speech/synthesize")
async def speech_synthesize(payload: dict):
    text = str(payload.get("text", "")).strip()
    voice = str(payload.get("voice", "alloy")).strip() or "alloy"
    if not text or len(text) > 5000:
        raise HTTPException(status_code=400, detail="text must contain 1-5000 characters")
    try:
        audio = await synthesize_speech(text, voice)
    except LLMError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(content=audio, media_type="audio/mpeg")


@app.post("/api/v2/agent/run", dependencies=[Depends(require_api_key)])
async def run_agent_v2(payload: dict):
    session_id = str(payload.get("session_id", "default"))
    goal = str(payload.get("goal", "")).strip()
    if not goal:
        raise HTTPException(status_code=400, detail="goal is required")
    service = RuntimeService(session_id, payload.get("confirm_token"))
    with metrics.timer("agent_runtime_seconds"):
        state = await service.run(goal)
    metrics.inc("agent_runs")
    return {
        "run_id": state.run_id,
        "status": state.status.value,
        "answer": state.final_answer,
        "error": state.error,
        "steps": state.budget.steps,
        "tool_calls": state.budget.tool_calls,
        "events": [{"kind": e.kind, "payload": e.payload} for e in state.events],
    }


@app.post("/api/v2/agent/stream", dependencies=[Depends(require_api_key)])
async def stream_agent_v2(payload: dict):
    session_id = str(payload.get("session_id", "default"))
    goal = str(payload.get("goal", "")).strip()
    if not goal:
        raise HTTPException(status_code=400, detail="goal is required")

    async def event_stream():
        import json

        service = RuntimeService(session_id, payload.get("confirm_token"))
        async for event in service.stream(goal):
            yield f"data: {json.dumps(event, default=str)}\\n\\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/v2/memory", dependencies=[Depends(require_api_key)])
async def remember_v2(payload: dict):
    try:
        kind = MemoryKind(str(payload.get("kind", "semantic")))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid memory kind") from exc
    text = str(payload.get("text", "")).strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    record = MemoryRecord(
        text=text,
        kind=kind,
        session_id=str(payload.get("session_id", "default")),
        importance=float(payload.get("importance", 0.5)),
        tags=list(payload.get("tags") or []),
    )
    MemoryManager().remember(record)
    return {"id": record.id, "kind": record.kind.value, "created_at": record.created_at}


@app.get("/api/v2/memory/search", dependencies=[Depends(require_api_key)])
async def memory_search_v2(session_id: str, q: str, limit: int = 8):
    records = MemoryManager().keyword_recall(session_id, q, min(max(limit, 1), 30))
    return {
        "results": [
            {"id": r.id, "text": r.text, "kind": r.kind.value, "importance": r.importance, "tags": r.tags}
            for r in records
        ]
    }


@app.get("/api/v2/metrics", dependencies=[Depends(require_api_key)])
async def metrics_v2():
    return metrics.snapshot()
