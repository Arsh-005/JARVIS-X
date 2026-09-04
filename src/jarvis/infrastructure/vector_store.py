from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class VectorPoint:
    id: str
    vector: list[float]
    payload: dict[str, Any]


class QdrantVectorStore:
    def __init__(self, url: str, api_key: str = "", collection: str = "jarvis-memory") -> None:
        try:
            from qdrant_client import QdrantClient
        except ImportError as exc:
            raise RuntimeError("Install the 'vector' extra to use Qdrant") from exc
        self._client = QdrantClient(url=url, api_key=api_key or None)
        self.collection = collection

    def ensure_collection(self, vector_size: int) -> None:
        from qdrant_client.models import Distance, VectorParams

        existing = {c.name for c in self._client.get_collections().collections}
        if self.collection not in existing:
            self._client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    def upsert(self, points: list[VectorPoint]) -> None:
        from qdrant_client.models import PointStruct

        self._client.upsert(
            collection_name=self.collection,
            points=[PointStruct(id=p.id, vector=p.vector, payload=p.payload) for p in points],
        )

    def search(self, vector: list[float], limit: int = 8, filter_: Any | None = None) -> list[dict[str, Any]]:
        results = self._client.search(
            collection_name=self.collection,
            query_vector=vector,
            query_filter=filter_,
            limit=limit,
            with_payload=True,
        )
        return [{"id": str(r.id), "score": float(r.score), "payload": r.payload or {}} for r in results]
