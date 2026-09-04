from __future__ import annotations

import contextvars
from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter
from uuid import uuid4

_trace_id = contextvars.ContextVar("trace_id", default="")


@dataclass(slots=True)
class Span:
    name: str
    trace_id: str
    duration_ms: float = 0.0
    error: str | None = None


@contextmanager
def trace(name: str):
    trace_id = _trace_id.get() or str(uuid4())

    token = _trace_id.set(trace_id)
    span = Span(name, trace_id)
    start = perf_counter()

    try:
        yield span

    except Exception as exc:
        span.error = f"{type(exc).__name__}: {exc}"
        raise

    finally:
        span.duration_ms = (perf_counter() - start) * 1000

        _trace_id.reset(token)
