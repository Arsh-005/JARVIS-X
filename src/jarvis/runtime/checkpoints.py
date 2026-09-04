from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class CheckpointStore:
    def __init__(self, root: Path | str = "data/checkpoints") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, run_id: str, payload: dict[str, Any]) -> Path:
        path = self.root / f"{run_id}.json"
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        temp.replace(path)
        return path

    def load(self, run_id: str) -> dict[str, Any] | None:
        path = self.root / f"{run_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
