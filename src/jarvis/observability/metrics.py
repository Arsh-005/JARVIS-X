from collections import Counter, defaultdict
from collections.abc import Generator
from contextlib import contextmanager
from threading import Lock
from time import perf_counter


class Metrics:
    """Thread-safe in-process metrics collector."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.counters: Counter[str] = Counter()
        self.timings: dict[str, list[float]] = defaultdict(list)

    def inc(
        self,
        name: str,
        value: int = 1,
    ) -> None:
        """Increment a named counter."""

        with self._lock:
            self.counters[name] += value

    @contextmanager
    def timer(
        self,
        name: str,
    ) -> Generator[None, None, None]:
        """Measure execution time for a named operation."""

        start = perf_counter()

        try:
            yield
        finally:
            elapsed = perf_counter() - start

            with self._lock:
                self.timings[name].append(elapsed)

    def snapshot(self) -> dict[str, object]:
        """Return a snapshot of the collected metrics."""

        with self._lock:
            return {
                "counters": dict(self.counters),
                "timings": {name: list(values) for name, values in self.timings.items()},
            }

    def clear(self) -> None:
        """Reset all collected metrics."""

        with self._lock:
            self.counters.clear()
            self.timings.clear()


# Shared application-wide metrics collector.
#
# Other modules use:
# from jarvis.observability.metrics import metrics
metrics = Metrics()
