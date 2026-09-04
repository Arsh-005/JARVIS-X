# JARVIS-X Multimodal UI Upgrade

This build upgrades the original Mission Control UI into a modern ChatGPT-style multimodal workspace while preserving the existing FastAPI/LLM/RAG/agent backend.

## Added

- Modern glassmorphism workspace and responsive sidebar
- Chat-style conversation layout with Markdown/code rendering and copy buttons
- New conversation workflow and starter prompts
- Drag-and-drop, file picker, and clipboard-paste attachments
- Multiple attachment previews and removal before sending
- Image analysis through `/api/vision/upload`
- Audio transcription through `/api/speech/transcribe`
- Text/JSON/CSV/PDF/DOCX ingestion through `/api/attachments/upload` into RAG
- Video/media upload storage with metadata (semantic video frame analysis remains a future extension)
- Knowledge mode and Agent mode toggles
- Browser speech recognition and speech synthesis controls
- Health/provider display
- Mobile responsive layout

## New dependencies

`pypdf` and `python-docx` are now core dependencies so PDF and DOCX attachments can be ingested.

Install/update with:

```powershell
pip install -e ".[dev,enterprise]"
```

Then run:

```powershell
uvicorn jarvis.api:app --reload
```

## Attachment limits

- Up to 8 files per message in the UI
- Up to 25 MB per general attachment
- Image endpoint keeps its existing 8 MB limit
- Audio endpoint keeps its existing 20 MB limit

## Video note

Videos can be selected, previewed as attachments, securely stored, and referenced in chat. This build intentionally does not pretend to understand video frames. Add a frame-extraction/vision pipeline later for full semantic video analysis.

## Secrets

This upgrade ZIP intentionally excludes `.env`, `.venv`, cache folders, local databases, audit logs and runtime checkpoints. Copy your local `.env` into the upgraded folder yourself; do not commit it.
