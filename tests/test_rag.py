from pathlib import Path

from jarvis.db import Database
from jarvis.rag import RAGStore, chunk_text


def test_chunk_text():
    chunks = chunk_text("A" * 2500, size=1000, overlap=100)
    assert len(chunks) >= 3


def test_rag_roundtrip(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    rag = RAGStore(db)
    rag.ingest("Python", "Python uses indentation and supports async programming.")
    results = rag.search("Python async")
    assert results
    assert results[0]["title"] == "Python"
