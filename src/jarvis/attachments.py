from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from jarvis.config import get_settings

MAX_FILE_BYTES = 25_000_000
MAX_EXTRACTED_CHARS = 120_000

TEXT_EXTENSIONS = {".txt", ".md", ".py", ".js", ".ts", ".html", ".css", ".yaml", ".yml", ".xml"}
DATA_EXTENSIONS = {".json", ".csv"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".webm", ".ogg"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
ALLOWED_EXTENSIONS = (
    TEXT_EXTENSIONS
    | DATA_EXTENSIONS
    | DOCUMENT_EXTENSIONS
    | IMAGE_EXTENSIONS
    | AUDIO_EXTENSIONS
    | VIDEO_EXTENSIONS
)


def safe_filename(filename: str) -> str:
    name = Path(filename or "attachment").name
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .")
    return name[:180] or "attachment"


def attachment_kind(suffix: str) -> str:
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in DOCUMENT_EXTENSIONS:
        return "document"
    return "file"


def _decode_text(raw: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="Could not decode this text file")


def extract_text(filename: str, raw: bytes) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix in TEXT_EXTENSIONS:
        return _decode_text(raw)[:MAX_EXTRACTED_CHARS]

    if suffix == ".json":
        try:
            parsed = json.loads(_decode_text(raw))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON file") from exc
        return json.dumps(parsed, ensure_ascii=False, indent=2)[:MAX_EXTRACTED_CHARS]

    if suffix == ".csv":
        text = _decode_text(raw)
        rows = list(csv.reader(io.StringIO(text)))
        rendered = "\n".join(" | ".join(row) for row in rows[:2000])
        return rendered[:MAX_EXTRACTED_CHARS]

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise HTTPException(status_code=503, detail="PDF support requires pypdf") from exc
        try:
            reader = PdfReader(io.BytesIO(raw))
            text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Could not read this PDF") from exc
        return text[:MAX_EXTRACTED_CHARS]

    if suffix == ".docx":
        try:
            from docx import Document
        except ImportError as exc:
            raise HTTPException(status_code=503, detail="DOCX support requires python-docx") from exc
        try:
            document = Document(io.BytesIO(raw))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Could not read this DOCX") from exc
        return text[:MAX_EXTRACTED_CHARS]

    return ""


async def save_upload(file: UploadFile) -> dict:
    filename = safe_filename(file.filename or "attachment")
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported attachment type: {suffix or 'unknown'}",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="The attachment is empty")
    if len(raw) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Attachment is larger than 25 MB")

    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}_{filename}"
    path = upload_dir / stored_name
    path.write_bytes(raw)

    text = extract_text(filename, raw)
    return {
        "id": uuid4().hex,
        "filename": filename,
        "stored_name": stored_name,
        "kind": attachment_kind(suffix),
        "content_type": file.content_type or "application/octet-stream",
        "size": len(raw),
        "text": text,
        "text_chars": len(text),
    }
