import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_dev_agent_unit_with_mock():
    """Le graphe doit retourner la réponse finale de l'agent ReAct (mock)."""
    from app.agents.dev import build_dev_graph
    from app.agents.state import DevState

    with patch("app.agents.dev.create_react_agent") as mock_react, \
         patch("app.agents.dev.ChatAnthropic") as mock_llm_class:
        fake_message = MagicMock()
        fake_message.content = "mocked claude reply"
        mock_react_agent = MagicMock()
        mock_react_agent.invoke.return_value = {"messages": [fake_message]}
        mock_react.return_value = mock_react_agent

        graph = build_dev_graph()
        result = graph.invoke(DevState(task="refactor X"))

        # LangGraph returns a dict-shaped state for Pydantic StateGraph too.
        response = result["response"] if isinstance(result, dict) else result.response
        assert response == "mocked claude reply"
        mock_llm_class.assert_called_once()
        mock_react.assert_called_once()


def test_dev_agent_flattens_block_content():
    """Si Claude renvoie content sous forme de blocks (tool calling), on extrait le texte."""
    from app.agents.dev import build_dev_graph
    from app.agents.state import DevState

    with patch("app.agents.dev.create_react_agent") as mock_react, \
         patch("app.agents.dev.ChatAnthropic"):
        fake_message = MagicMock()
        fake_message.content = [{"type": "text", "text": "bloc1 "}, {"type": "text", "text": "bloc2"}]
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"messages": [fake_message]}
        mock_react.return_value = mock_agent

        graph = build_dev_graph()
        result = graph.invoke(DevState(task="test"))

        response = result["response"] if isinstance(result, dict) else result.response
        assert response == "bloc1 bloc2"


def test_dev_agent_uses_conversation_history():
    """Quand DevState porte un historique, l'agent ReAct le reçoit en entier
    (après le SystemMessage) — c'est le mécanisme de mémoire Phase 2."""
    from langchain_core.messages import AIMessage, HumanMessage

    from app.agents.dev import build_dev_graph
    from app.agents.state import DevState

    with patch("app.agents.dev.create_react_agent") as mock_react, \
         patch("app.agents.dev.ChatAnthropic"):
        fake_message = MagicMock()
        fake_message.content = "réponse contextuelle"
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"messages": [fake_message]}
        mock_react.return_value = mock_agent

        history = [
            HumanMessage(content="comment marche team.py ?"),
            AIMessage(content="c'est un supervisor LangGraph"),
            HumanMessage(content="et le repo ?"),
        ]
        build_dev_graph().invoke(DevState(task="et le repo ?", messages=history))

        sent = mock_agent.invoke.call_args.args[0]["messages"]
        # SystemMessage en tête, puis les 3 messages d'historique tels quels.
        assert [m.content for m in sent[1:]] == [
            "comment marche team.py ?",
            "c'est un supervisor LangGraph",
            "et le repo ?",
        ]


def test_dev_agent_falls_back_to_task_when_no_history():
    """Sans historique (one-shot /agents/dev/run), l'agent reçoit un unique
    HumanMessage construit depuis ``task``."""
    from app.agents.dev import build_dev_graph
    from app.agents.state import DevState

    with patch("app.agents.dev.create_react_agent") as mock_react, \
         patch("app.agents.dev.ChatAnthropic"):
        fake_message = MagicMock()
        fake_message.content = "ok"
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"messages": [fake_message]}
        mock_react.return_value = mock_agent

        build_dev_graph().invoke(DevState(task="question isolée"))

        sent = mock_agent.invoke.call_args.args[0]["messages"]
        assert len(sent) == 2  # SystemMessage + HumanMessage
        assert sent[1].content == "question isolée"


def test_run_dev_agent_endpoint_with_mock():
    """POST /agents/dev/run renvoie l'enveloppe AgentResponse (graphe mocké)."""
    with patch("app.routers.agents.dev_graph") as mock_graph:
        mock_graph.invoke.return_value = {
            "task": "test",
            "response": "stubbed response",
        }
        response = client.post("/agents/dev/run", json={"task": "test"})

        assert response.status_code == 200
        body = response.json()
        assert body["agent"] == "dev"
        assert body["response"] == "stubbed response"
        assert body["metadata"] == {}


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
    from app.agents.state import DevState

    graph = build_dev_graph()
    result = graph.invoke(DevState(task="Reponds juste avec le mot 'ok' et rien d'autre."))
    response = result["response"] if isinstance(result, dict) else result.response
    assert isinstance(response, str)
    assert len(response) > 0
