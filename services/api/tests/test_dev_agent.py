import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_dev_agent_unit_with_mock():
    """Le graphe doit retourner la réponse du LLM (mock)."""
    from app.agents.dev import build_dev_graph

    with patch("app.agents.dev.ChatAnthropic") as mock_llm_class:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="mocked claude reply")
        mock_llm_class.return_value = mock_llm

        graph = build_dev_graph()
        result = graph.invoke({"task": "refactor X", "response": ""})

        assert result["response"] == "mocked claude reply"
        mock_llm_class.assert_called_once()


def test_run_dev_agent_endpoint_with_mock():
    """POST /agents/dev/run renvoie agent + response (graphe mocké)."""
    with patch("app.routers.agents.dev_graph") as mock_graph:
        mock_graph.invoke.return_value = {
            "task": "test",
            "response": "stubbed response",
        }
        response = client.post("/agents/dev/run", json={"task": "test"})

        assert response.status_code == 200
        assert response.json() == {"agent": "dev", "response": "stubbed response"}


def test_run_dev_agent_endpoint_validates_empty_task():
    """Une tâche vide doit être rejetée (422)."""
    response = client.post("/agents/dev/run", json={"task": ""})
    assert response.status_code == 422


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "").startswith("sk-ant-api03-CHANGE_ME"),
    reason="ANTHROPIC_API_KEY non configuree",
)
def test_dev_agent_integration_real_claude():
    """Appel reel a Claude Haiku, skip si pas de cle."""
    from app.agents.dev import build_dev_graph

    graph = build_dev_graph()
    result = graph.invoke(
        {"task": "Reponds juste avec le mot 'ok' et rien d'autre.", "response": ""}
    )
    assert isinstance(result["response"], str)
    assert len(result["response"]) > 0
