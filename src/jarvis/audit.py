import json
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from jarvis.config import get_settings

_lock = Lock()


def audit(event: str, payload: dict[str, Any]) -> None:
    path = get_settings().audit_log_path
    record = {"timestamp": datetime.now(UTC).isoformat(), "event": event, "payload": payload}
    with _lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
