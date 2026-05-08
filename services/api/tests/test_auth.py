from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_post_without_token_returns_401(monkeypatch, enable_auth):
    monkeypatch.setenv("KISNLAB_API_TOKEN", "expected-token")
    response = client.post("/agents/dev/run", json={"task": "test"})
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


def test_post_with_wrong_token_returns_401(monkeypatch, enable_auth):
    monkeypatch.setenv("KISNLAB_API_TOKEN", "expected-token")
    response = client.post(
        "/agents/dev/run",
        json={"task": "test"},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401


def test_post_with_valid_token_passes_auth(monkeypatch, enable_auth):
    monkeypatch.setenv("KISNLAB_API_TOKEN", "expected-token")
    with patch("app.routers.agents.dev_graph") as mock_graph:
        mock_graph.invoke.return_value = {"task": "test", "response": "stub"}
        response = client.post(
            "/agents/dev/run",
            json={"task": "test"},
            headers={"Authorization": "Bearer expected-token"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["agent"] == "dev"
        assert body["response"] == "stub"
        assert body["metadata"] == {}


def test_health_does_not_require_auth(enable_auth, monkeypatch):
    monkeypatch.setenv("KISNLAB_API_TOKEN", "expected-token")
    response = client.get("/health")
    assert response.status_code == 200


def test_post_returns_503_when_token_not_configured(monkeypatch, enable_auth):
    monkeypatch.delenv("KISNLAB_API_TOKEN", raising=False)
    response = client.post(
        "/agents/dev/run",
        json={"task": "test"},
        headers={"Authorization": "Bearer anything"},
    )
    assert response.status_code == 503
