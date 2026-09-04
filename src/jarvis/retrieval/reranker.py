from __future__ import annotations

import re

from jarvis.retrieval.hybrid import RetrievedChunk


class LightweightReranker:
    def rerank(self, query: str, chunks: list[RetrievedChunk], limit: int = 5) -> list[RetrievedChunk]:
        q = set(re.findall(r"\w+", query.lower()))
        for c in chunks:
            terms = set(re.findall(r"\w+", c.text.lower()))
            coverage = len(q & terms) / max(len(q), 1)
            phrase = 1.0 if query.lower() in c.text.lower() else 0.0
            c.final_score = c.final_score * 0.75 + coverage * 0.2 + phrase * 0.05
        return sorted(chunks, key=lambda x: x.final_score, reverse=True)[:limit]
