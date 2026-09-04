from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EvalCase:
    query: str
    expected_terms: list[str]


@dataclass(slots=True)
class EvalResult:
    query: str
    recall: float
    passed: bool


def evaluate_retrieval(search, cases: list[EvalCase], k: int = 5) -> list[EvalResult]:
    out = []
    for case in cases:
        rows = search(case.query, k)
        text = " ".join(str(r) for r in rows).lower()
        hits = sum(term.lower() in text for term in case.expected_terms)
        recall = hits / max(len(case.expected_terms), 1)
        out.append(EvalResult(case.query, recall, recall >= 0.5))
    return out
