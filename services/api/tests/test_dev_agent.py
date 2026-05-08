import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_dev_agent_unit_with_mock():
    """Le graphe doit retourner la réponse finale de l'agent ReAct (mock)."""
    from app.agents.dev import build_dev_graph

    with patch("app.agents.dev.create_react_agent") as mock_react, \
         patch("app.agents.dev.ChatAnthropic") as mock_llm_class:
        fake_message = MagicMock()
        fake_message.content = "mocked claude reply"
        mock_react_agent = MagicMock()
        mock_react_agent.invoke.return_value = {"messages": [fake_message]}
        mock_react.return_value = mock_react_agent

        graph = build_dev_graph()
        result = graph.invoke({"task": "refactor X", "response": ""})

        assert result["response"] == "mocked claude reply"
        mock_llm_class.assert_called_once()
        mock_react.assert_called_once()


def test_dev_agent_flattens_block_content():
    """Si Claude renvoie content sous forme de blocks (tool calling), on extrait le texte."""
    from app.agents.dev import build_dev_graph

    with patch("app.agents.dev.create_react_agent") as mock_react, \
         patch("app.agents.dev.ChatAnthropic"):
        fake_message = MagicMock()
        fake_message.content = [{"type": "text", "text": "bloc1 "}, {"type": "text", "text": "bloc2"}]
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"messages": [fake_message]}
        mock_react.return_value = mock_agent

        graph = build_dev_graph()
        result = graph.invoke({"task": "test", "response": ""})

        assert result["response"] == "bloc1 bloc2"


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
