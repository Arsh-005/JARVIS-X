from __future__ import annotations


def build_metrics_response() -> tuple[bytes, str]:
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    except ImportError as exc:
        raise RuntimeError("Install the 'observability' extra to expose Prometheus metrics") from exc
    return generate_latest(), CONTENT_TYPE_LATEST
