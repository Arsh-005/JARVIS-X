import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from jarvis.config import get_settings


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or get_settings().database_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                vector_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """)

    def add_message(self, session_id: str, role: str, content: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO messages(session_id, role, content, created_at) VALUES(?,?,?,?)",
                (session_id, role, content, utc_now()),
            )

    def get_messages(self, session_id: str, limit: int = 20) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT role, content, created_at FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def add_memory(self, session_id: str, kind: str, content: str, metadata: dict | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO memories(session_id, kind, content, metadata_json, created_at) VALUES(?,?,?,?,?)",
                (session_id, kind, content, json.dumps(metadata or {}), utc_now()),
            )

    def get_memories(self, session_id: str, limit: int = 10) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT kind, content, metadata_json, created_at FROM memories WHERE session_id=? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [dict(r) | {"metadata": json.loads(r["metadata_json"])} for r in rows]

    def add_chunk(
        self, document_id: str, title: str, source: str, index: int, content: str, vector: list[float]
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO chunks(document_id,title,source,chunk_index,content,vector_json,created_at) VALUES(?,?,?,?,?,?,?)",
                (document_id, title, source, index, content, json.dumps(vector), utc_now()),
            )

    def all_chunks(self) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM chunks ORDER BY id").fetchall()
        return [dict(r) | {"vector": json.loads(r["vector_json"])} for r in rows]
