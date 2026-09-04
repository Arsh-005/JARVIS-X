from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ScreenFrame:
    path: Path
    width: int
    height: int


def capture_screen(output: str | Path = "data/screens/latest.png") -> ScreenFrame:
    try:
        from PIL import ImageGrab
    except ImportError as exc:
        raise RuntimeError("Install jarvis-x[desktop] for screen capture") from exc
    image = ImageGrab.grab()
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)

    image.save(path)
    return ScreenFrame(path, image.width, image.height)
