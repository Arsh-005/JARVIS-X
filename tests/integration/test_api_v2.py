from fastapi.testclient import TestClient

from jarvis.api import app

client = TestClient(app)


def test_metrics_endpoint_no_key_configured():
    response = client.get("/api/v2/metrics")
    assert response.status_code == 200
    assert "counters" in response.json()


def test_memory_endpoints(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    response = client.post(
        "/api/v2/memory", json={"session_id": "s", "kind": "project", "text": "JARVIS uses agent budgets"}
    )
    assert response.status_code == 200
    response = client.get("/api/v2/memory/search", params={"session_id": "s", "q": "agent budgets"})
    assert response.status_code == 200
    assert response.json()["results"]
