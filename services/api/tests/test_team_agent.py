"""Team supervisor: route → delegate.

Routing decisions are LLM-driven so unit tests mock the LLM. We verify:
- prompt structure passed to the router LLM,
- correct dispatch to dev_graph vs reviewer_graph based on the LLM output,
- fallback to dev when the LLM call raises,
- 422 when the inner reviewer raises ValueError,
- response shape (metadata.routed_to).

Real-LLM routing intelligence is exercised by the parametrized integration
tests at the bottom (skipped without ANTHROPIC_API_KEY).
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from app.agents.state import TeamState
from app.agents.team import ROUTER_SYSTEM, _Route, build_team_graph
from app.main import app

client = TestClient(app)


# === Helpers ===


def _mock_router_returning(agent: str):
    """Build a ChatAnthropic mock whose with_structured_output(...).invoke
    returns ``_Route(agent=agent)``."""
    structured = MagicMock()
    structured.invoke.return_value = _Route(agent=agent)  # type: ignore[arg-type]
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    return llm, structured


def _stub_subgraph(response: str = "stubbed", **extra):
    g = MagicMock()
    g.invoke.return_value = {"response": response, **extra}
    return g


# === Routing dispatch ===


class TestRouting:
    @pytest.mark.parametrize(
        "agent_decision, expected_called",
        [
            ("dev", "dev"),
            ("reviewer", "reviewer"),
        ],
    )
    def test_routes_to_correct_subgraph(self, agent_decision, expected_called):
        dev_g = _stub_subgraph("dev reply")
        rev_g = _stub_subgraph("reviewer reply", perspectives=[])

        with patch("app.agents.team.ChatAnthropic") as mock_anth:
            llm, _ = _mock_router_returning(agent_decision)
            mock_anth.return_value = llm

            graph = build_team_graph(dev_graph=dev_g, reviewer_graph=rev_g)
            result = graph.invoke(TeamState(task="any task"))

            routed_to = result["routed_to"] if isinstance(result, dict) else result.routed_to
            response = result["response"] if isinstance(result, dict) else result.response

            assert routed_to == expected_called
            if expected_called == "dev":
                dev_g.invoke.assert_called_once()
                rev_g.invoke.assert_not_called()
                assert response == "dev reply"
            else:
                rev_g.invoke.assert_called_once()
                dev_g.invoke.assert_not_called()
                assert response == "reviewer reply"

    def test_router_prompt_carries_task_and_system(self):
        dev_g = _stub_subgraph()
        rev_g = _stub_subgraph(perspectives=[])

        with patch("app.agents.team.ChatAnthropic") as mock_anth:
            llm, structured = _mock_router_returning("dev")
            mock_anth.return_value = llm

            build_team_graph(dev_graph=dev_g, reviewer_graph=rev_g).invoke(
                TeamState(task="refactor login flow")
            )

            messages = structured.invoke.call_args.args[0]
            assert messages[0].content == ROUTER_SYSTEM
            assert "refactor login flow" in messages[1].content
            assert structured.invoke.call_args.kwargs["config"]["run_name"] == "team_router"

    def test_llm_failure_falls_back_to_dev(self):
        dev_g = _stub_subgraph("fallback reply")
        rev_g = _stub_subgraph(perspectives=[])

        with patch("app.agents.team.ChatAnthropic") as mock_anth:
            structured = MagicMock()
            structured.invoke.side_effect = RuntimeError("anthropic 529")
            llm = MagicMock()
            llm.with_structured_output.return_value = structured
            mock_anth.return_value = llm

            graph = build_team_graph(dev_graph=dev_g, reviewer_graph=rev_g)
            result = graph.invoke(TeamState(task="anything"))

            routed_to = result["routed_to"] if isinstance(result, dict) else result.routed_to
            assert routed_to == "dev"
            dev_g.invoke.assert_called_once()
            rev_g.invoke.assert_not_called()

    def test_reviewer_value_error_propagates_to_caller(self):
        """Le reviewer peut raise ValueError (parse PR ref impossible).
        Le team graph ne masque PAS l'erreur — c'est au router HTTP de la
        traduire en 422.
        """
        dev_g = _stub_subgraph()
        rev_g = MagicMock()
        rev_g.invoke.side_effect = ValueError("PR ref non trouvée")

        with patch("app.agents.team.ChatAnthropic") as mock_anth:
            llm, _ = _mock_router_returning("reviewer")
            mock_anth.return_value = llm

            graph = build_team_graph(dev_graph=dev_g, reviewer_graph=rev_g)
            with pytest.raises(ValueError):
                graph.invoke(TeamState(task="review please"))


# === Conversation memory (Phase 2) ===


def _capturing_dev_graph(seen: list):
    """Stub dev sub-graph qui enregistre les messages reçus à chaque appel."""
    def dev_invoke(state, config=None):
        seen.append([m.content for m in state.messages])
        return {"response": f"réponse {len(seen)}"}

    g = MagicMock()
    g.invoke.side_effect = dev_invoke
    return g


class TestConversationMemory:
    def test_history_accumulates_across_turns_same_thread(self):
        """Sur un même thread_id, le sous-agent dev voit l'historique cumulé :
        questions ET réponses des tours précédents."""
        seen: list = []
        dev_g = _capturing_dev_graph(seen)
        rev_g = _stub_subgraph(perspectives=[])

        with patch("app.agents.team.ChatAnthropic") as mock_anth:
            llm, _ = _mock_router_returning("dev")
            mock_anth.return_value = llm

            graph = build_team_graph(
                dev_graph=dev_g, reviewer_graph=rev_g, checkpointer=MemorySaver()
            )
            config = {"configurable": {"thread_id": "chan-1"}}
            for turn in ("première question", "deuxième question", "troisième question"):
                graph.invoke(
                    TeamState(task=turn, messages=[HumanMessage(content=turn)]),
                    config=config,
                )

        # Tour 1 : dev ne voit que sa propre question.
        assert seen[0] == ["première question"]
        # Tour 3 : dev voit les 3 questions + les 2 réponses précédentes.
        assert "première question" in seen[2]
        assert "deuxième question" in seen[2]
        assert "troisième question" in seen[2]
        assert "réponse 1" in seen[2]
        assert "réponse 2" in seen[2]

    def test_distinct_threads_do_not_share_history(self):
        """Deux thread_id différents (= deux channels Discord) sont isolés."""
        seen: list = []
        dev_g = _capturing_dev_graph(seen)
        rev_g = _stub_subgraph(perspectives=[])

        with patch("app.agents.team.ChatAnthropic") as mock_anth:
            llm, _ = _mock_router_returning("dev")
            mock_anth.return_value = llm

            graph = build_team_graph(
                dev_graph=dev_g, reviewer_graph=rev_g, checkpointer=MemorySaver()
            )
            graph.invoke(
                TeamState(task="sujet A", messages=[HumanMessage(content="sujet A")]),
                config={"configurable": {"thread_id": "chan-A"}},
            )
            graph.invoke(
                TeamState(task="sujet B", messages=[HumanMessage(content="sujet B")]),
                config={"configurable": {"thread_id": "chan-B"}},
            )

        assert seen[0] == ["sujet A"]
        assert seen[1] == ["sujet B"]  # pas de fuite du thread A

    def test_stateless_when_no_checkpointer(self):
        """Sans checkpointer (Phase 1), chaque invoke repart de zéro."""
        seen: list = []
        dev_g = _capturing_dev_graph(seen)
        rev_g = _stub_subgraph(perspectives=[])

        with patch("app.agents.team.ChatAnthropic") as mock_anth:
            llm, _ = _mock_router_returning("dev")
            mock_anth.return_value = llm

            graph = build_team_graph(dev_graph=dev_g, reviewer_graph=rev_g)
            graph.invoke(TeamState(task="q1", messages=[HumanMessage(content="q1")]))
            graph.invoke(TeamState(task="q2", messages=[HumanMessage(content="q2")]))

        assert seen[0] == ["q1"]
        assert seen[1] == ["q2"]  # aucun cumul


# === Endpoint ===


class TestTeamEndpoint:
    def test_team_endpoint_returns_routed_to_metadata(self):
        with patch("app.routers.agents.team_graph") as mock_graph:
            mock_graph.invoke.return_value = {
                "task": "test",
                "routed_to": "reviewer",
                "response": "# Review",
            }
            res = client.post("/agents/team/run", json={"task": "kisnco/kisnlab#7"})
            assert res.status_code == 200
            body = res.json()
            assert body["agent"] == "team"
            assert body["response"] == "# Review"
            assert body["metadata"] == {"routed_to": "reviewer"}

    def test_team_endpoint_translates_value_error_to_422(self):
        with patch("app.routers.agents.team_graph") as mock_graph:
            mock_graph.invoke.side_effect = ValueError("PR ref introuvable")
            res = client.post("/agents/team/run", json={"task": "review please"})
            assert res.status_code == 422
            assert "PR ref" in res.json()["detail"]

    def test_team_endpoint_validates_empty_task(self):
        res = client.post("/agents/team/run", json={"task": ""})
        assert res.status_code == 422

    def test_team_endpoint_forwards_thread_id_to_config(self):
        """Le thread_id de la requête arrive bien dans le config LangGraph."""
        with patch("app.routers.agents.team_graph") as mock_graph:
            mock_graph.invoke.return_value = {
                "task": "t", "routed_to": "dev", "response": "r",
            }
            client.post(
                "/agents/team/run",
                json={"task": "salut", "thread_id": "discord:42"},
            )
            config = mock_graph.invoke.call_args.kwargs["config"]
            assert config["configurable"]["thread_id"] == "discord:42"

    def test_team_endpoint_uses_ephemeral_thread_when_absent(self):
        """Sans thread_id, le router génère une clé éphémère → appel one-shot."""
        with patch("app.routers.agents.team_graph") as mock_graph:
            mock_graph.invoke.return_value = {
                "task": "t", "routed_to": "dev", "response": "r",
            }
            client.post("/agents/team/run", json={"task": "salut"})
            config = mock_graph.invoke.call_args.kwargs["config"]
            assert config["configurable"]["thread_id"].startswith("ephemeral:")


# === Real LLM routing (skipped without API key) ===

ANTHROPIC_OK = bool(os.getenv("ANTHROPIC_API_KEY")) and not os.getenv(
    "ANTHROPIC_API_KEY", ""
).startswith("sk-ant-api03-CHANGE_ME")


@pytest.mark.skipif(not ANTHROPIC_OK, reason="ANTHROPIC_API_KEY non configurée")
@pytest.mark.parametrize(
    "task, expected",
    [
        ("Review la PR kisnco/kisnlab#7 stp", "reviewer"),
        ("Regarde https://github.com/owner/repo/pull/42", "reviewer"),
        ("Refactor le module d'auth en Symfony", "dev"),
        ("Comment Python gère-t-il les coroutines ?", "dev"),
        ("Salut, tu peux m'aider ?", "dev"),  # ambigu → fallback dev
        ("Écris une fonction Fibonacci en Rust", "dev"),
    ],
)
def test_real_llm_routes_correctly(task: str, expected: str):
    """Routing intelligence — calls real Claude. Skipped en CI sans clé."""
    from app.agents.team import route as route_node

    decision = route_node(TeamState(task=task))
    assert decision["routed_to"] == expected, f"task={task!r} got {decision['routed_to']!r}"
