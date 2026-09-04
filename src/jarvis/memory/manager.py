from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path

from jarvis.memory.models import MemoryKind, MemoryRecord


class MemoryManager:
    def __init__(self, path: str | Path = "data/memory.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def _init(self) -> None:
        with self._connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS memories(
                id TEXT PRIMARY KEY, session_id TEXT NOT NULL, kind TEXT NOT NULL,
                text TEXT NOT NULL, importance REAL NOT NULL, tags TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""")
            con.execute("CREATE INDEX IF NOT EXISTS idx_mem_session_kind ON memories(session_id, kind)")

    def remember(self, record: MemoryRecord) -> MemoryRecord:
        with self._connect() as con:
            con.execute(
                "INSERT OR REPLACE INTO memories VALUES(?,?,?,?,?,?,?)",
                (
                    record.id,
                    record.session_id,
                    record.kind.value,
                    record.text,
                    record.importance,
                    json.dumps(record.tags),
                    record.created_at,
                ),
            )
        return record

    def recent(self, session_id: str, kind: MemoryKind | None = None, limit: int = 20) -> list[MemoryRecord]:
        sql = "SELECT * FROM memories WHERE session_id=?"
        args: list[object] = [session_id]
        if kind:
            sql += " AND kind=?"
            args.append(kind.value)
        sql += " ORDER BY created_at DESC LIMIT ?"
        args.append(limit)
        with self._connect() as con:
            rows = con.execute(sql, args).fetchall()
        return [
            MemoryRecord(
                id=r["id"],
                session_id=r["session_id"],
                kind=MemoryKind(r["kind"]),
                text=r["text"],
                importance=r["importance"],
                tags=json.loads(r["tags"]),
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def keyword_recall(self, session_id: str, query: str, limit: int = 8) -> list[MemoryRecord]:
        terms = {t.lower() for t in query.split() if len(t) > 2}
        scored = []
        for record in self.recent(session_id, limit=200):
            words = set(record.text.lower().split())
            overlap = len(terms & words)
            score = overlap + math.log1p(max(record.importance, 0.0))
            if overlap:
                scored.append((score, record))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:limit]]
