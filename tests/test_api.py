from fastapi.testclient import TestClient

from jarvis.api import app
from jarvis.config import get_settings

client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_local_chat(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "local")

    # IMPORTANT:
    # get_settings() uses @lru_cache.
    # Clear the cached Settings object so the new
    # LLM_PROVIDER environment variable is read.
    get_settings.cache_clear()

    response = client.post(
        "/api/chat",
        json={
            "message": "hello",
            "session_id": "test-local",
            "use_rag": False,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["provider"] == "local"
    assert "local fallback mode" in data["answer"]

    # Clear again so this test does not affect later tests.
    get_settings.cache_clear()
