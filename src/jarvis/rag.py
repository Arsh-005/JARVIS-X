from uuid import uuid4

from jarvis.db import Database
from jarvis.embeddings import cosine, hashed_embedding, lexical_overlap


def chunk_text(text: str, size: int = 1200, overlap: int = 180) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = max(text.rfind("\n", start, end), text.rfind(". ", start, end))
            if boundary > start + size // 2:
                end = boundary + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return [c for c in chunks if c]


class RAGStore:
    def __init__(self, db: Database | None = None) -> None:
        self.db = db or Database()

    def ingest(self, title: str, text: str, source: str = "manual") -> dict:
        document_id = str(uuid4())
        chunks = chunk_text(text)
        for index, chunk in enumerate(chunks):
            self.db.add_chunk(document_id, title, source, index, chunk, hashed_embedding(chunk))
        return {"document_id": document_id, "title": title, "chunks": len(chunks), "source": source}

    def search(self, query: str, limit: int = 5) -> list[dict]:
        qvec = hashed_embedding(query)
        results = []
        for row in self.db.all_chunks():
            semantic = cosine(qvec, row["vector"])
            lexical = lexical_overlap(query, row["content"])
            score = 0.75 * semantic + 0.25 * lexical
            results.append(
                {
                    "score": round(score, 4),
                    "document_id": row["document_id"],
                    "title": row["title"],
                    "source": row["source"],
                    "chunk_index": row["chunk_index"],
                    "content": row["content"],
                }
            )
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
