from jarvis.retrieval.hybrid import HybridRetriever, RetrievedChunk
from jarvis.retrieval.reranker import LightweightReranker


def test_hybrid_and_rerank():
    docs = [
        RetrievedChunk("1", "FastAPI powers the agent API", "a"),
        RetrievedChunk("2", "banana recipe", "b"),
    ]
    r = HybridRetriever(alpha=0.2)
    ranked = r.fuse(r.sparse_scores("FastAPI agent", docs), 2)
    ranked = LightweightReranker().rerank("FastAPI agent", ranked, 2)
    assert ranked[0].id == "1"
