"""LangGraph team supervisor: route une tâche vers ``dev`` ou ``reviewer``.

Pipeline :

```
START → route → delegate → END
```

- ``route`` : Claude Haiku avec ``with_structured_output(_Route)`` — décision déterministe (`dev` | `reviewer`). Fallback ``dev`` si l'appel LLM plante.
- ``delegate`` : invoque le sub-graph ciblé avec son state propre.

Les sub-graphes sont construits une fois au build pour éviter les recompilations
par appel. Ils sont injectables via ``build_team_graph(dev_graph=..., reviewer_graph=...)``
pour faciliter les tests.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.dev import build_dev_graph
from app.agents.reviewer import build_reviewer_graph
from app.agents.state import AgentName, DevState, ReviewerState, TeamState

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"

ROUTER_SYSTEM = (
    "Tu es le superviseur de l'équipe dev KisnLab. "
    "Tu décides quel sous-agent doit traiter une tâche utilisateur.\n\n"
    "Sous-agents disponibles :\n\n"
    "- `dev` : tâches techniques générales (code, debug, refactor, archi, "
    "exploration, questions ouvertes). C'est le **fallback par défaut** "
    "quand le routage est ambigu.\n"
    "- `reviewer` : review d'une PR GitHub spécifique. La tâche doit "
    "contenir une référence claire à une PR (URL `github.com/.../pull/N`, "
    "raccourci `owner/repo#N`, ou mention narrative `PR #N de owner/repo`).\n\n"
    "Règle : si la tâche n'évoque pas explicitement une PR à reviewer, "
    "route vers `dev`."
)


class _Route(BaseModel):
    """Schéma demandé au LLM pour la décision de routage."""

    agent: AgentName = Field(..., description="Sous-agent qui doit traiter la tâche.")


def _build_langfuse_callbacks() -> list[Any]:
    if not (os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")):
        return []
    try:
        from langfuse.langchain import CallbackHandler

        return [CallbackHandler()]
    except Exception as exc:
        logger.warning("Langfuse tracing disabled (callback unavailable): %s", exc)
        return []


_LANGFUSE_CALLBACKS: list[Any] = _build_langfuse_callbacks()


def _read(result: Any, field: str) -> Any:
    """LangGraph state may be a dict or the BaseModel; normalize."""
    return result[field] if isinstance(result, dict) else getattr(result, field)


def route(state: TeamState) -> dict:
    """Demande à Claude Haiku quel sous-agent doit traiter la tâche."""
    llm = ChatAnthropic(model=MODEL, max_tokens=64).with_structured_output(_Route)
    try:
        result: _Route = llm.invoke(
            [
                SystemMessage(content=ROUTER_SYSTEM),
                HumanMessage(content=f"Tâche : {state.task}"),
            ],
            config={
                "callbacks": _LANGFUSE_CALLBACKS,
                "run_name": "team_router",
            },
        )
        return {"routed_to": result.agent}
    except Exception as exc:
        logger.warning("team router failed (%s) — falling back to dev", exc)
        return {"routed_to": "dev"}


def _make_delegate(dev_graph, reviewer_graph) -> Callable[[TeamState], dict]:
    def delegate(state: TeamState) -> dict:
        if state.routed_to == "reviewer":
            sub = reviewer_graph.invoke(ReviewerState(task=state.task))
        else:
            sub = dev_graph.invoke(DevState(task=state.task))
        return {"response": _read(sub, "response")}

    return delegate


def build_team_graph(dev_graph=None, reviewer_graph=None):
    dev_graph = dev_graph if dev_graph is not None else build_dev_graph()
    reviewer_graph = reviewer_graph if reviewer_graph is not None else build_reviewer_graph()

    graph = StateGraph(TeamState)
    graph.add_node("route", route)
    graph.add_node("delegate", _make_delegate(dev_graph, reviewer_graph))
    graph.add_edge(START, "route")
    graph.add_edge("route", "delegate")
    graph.add_edge("delegate", END)
    return graph.compile()
