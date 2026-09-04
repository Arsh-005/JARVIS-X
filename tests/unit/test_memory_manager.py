from jarvis.memory.manager import MemoryManager
from jarvis.memory.models import MemoryKind, MemoryRecord


def test_memory_round_trip(tmp_path):
    manager = MemoryManager(tmp_path / "m.db")
    manager.remember(
        MemoryRecord("Project Atlas uses FastAPI", MemoryKind.PROJECT, "s", importance=0.9, tags=["atlas"])
    )
    rows = manager.keyword_recall("s", "Atlas FastAPI")
    assert rows and "FastAPI" in rows[0].text
