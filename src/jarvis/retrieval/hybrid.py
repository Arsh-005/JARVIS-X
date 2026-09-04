from __future__ import annotations

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(slots=True)
class RetrievedChunk:
    id: str
    text: str
    source: str
    dense_score: float = 0.0
    sparse_score: float = 0.0
    final_score: float = 0.0


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


class HybridRetriever:
    """Dependency-light hybrid retrieval using BM25-like sparse ranking plus optional dense scores."""

    def __init__(self, alpha: float = 0.6) -> None:
        self.alpha = min(1.0, max(0.0, alpha))

    def sparse_scores(self, query: str, chunks: Iterable[RetrievedChunk]) -> list[RetrievedChunk]:
        docs = list(chunks)
        q = _tokens(query)
        if not docs or not q:
            return docs
        tokenized = [_tokens(d.text) for d in docs]
        avgdl = sum(map(len, tokenized)) / max(len(tokenized), 1)
        df = {term: sum(term in set(doc) for doc in tokenized) for term in set(q)}
        for item, doc in zip(
            docs,
            tokenized,
            strict=True,
        ):
            score = 0.0
            for term in q:
                tf = doc.count(term)
                n = df.get(term, 0)
                idf = math.log(1 + (len(docs) - n + 0.5) / (n + 0.5))
                denom = tf + 1.5 * (1 - 0.75 + 0.75 * len(doc) / max(avgdl, 1))
                score += idf * (tf * 2.5 / denom if denom else 0)
            item.sparse_score = score
        return docs

    def fuse(self, chunks: Iterable[RetrievedChunk], limit: int = 5) -> list[RetrievedChunk]:
        docs = list(chunks)
        max_sparse = max((d.sparse_score for d in docs), default=1) or 1
        max_dense = max((d.dense_score for d in docs), default=1) or 1
        for d in docs:
            d.final_score = self.alpha * (d.dense_score / max_dense) + (1 - self.alpha) * (
                d.sparse_score / max_sparse
            )
        return sorted(docs, key=lambda d: d.final_score, reverse=True)[:limit]
