"""LangGraph reviewer agent: 3 perspectives en parallèle sur un diff PR.

Pipeline :

```
START → prepare → fan_out → assess_security    ┐
                          → assess_quality    ─┼→ synthesize → END
                          → assess_architecture┘
```

Le diff est récupéré une seule fois dans ``prepare`` puis injecté en bloc
``cache_control: ephemeral`` dans le system message des 3 perspectives.
Anthropic met le diff en cache au premier appel et le réutilise sur les
deux suivants (~½ coût vs 3 appels indépendants).
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.skills import load_skills
from app.agents.state import (
    Perspective,
    PerspectiveOpinion,
    ReviewerState,
    Severity,
)
from app.agents.tools.github_tools import gh_pr_diff

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"

PERSPECTIVES: tuple[Perspective, ...] = ("security", "quality", "architecture")
PERSPECTIVE_SKILLS: dict[Perspective, str] = {
    "security": "security_review",
    "quality": "quality_review",
    "architecture": "architecture_review",
}

REVIEWER_SYSTEM_PREFIX = (
    "Tu es un sous-agent reviewer de KisnLab. "
    "Tu analyses un diff GitHub et tu réponds en français, concis et actionnable. "
    "Tu produis une opinion structurée : `findings` (markdown court) et `severity`.\n\n"
    "DIFF À ANALYSER :\n\n"
)

SEVERITY_ORDER: dict[Severity, int] = {"block": 0, "warn": 1, "info": 2}


# === PR ref parsing ===

_PR_REF_PATTERNS = (
    re.compile(r"github\.com/([\w.-]+/[\w.-]+)/pull/(\d+)"),
    re.compile(r"([\w.-]+/[\w.-]+)#(\d+)"),
    re.compile(r"#(\d+)\s+(?:in|of|de|du|dans|sur|on)\s+([\w.-]+/[\w.-]+)", re.IGNORECASE),
)


def _parse_pr_ref(task: str) -> tuple[str, int]:
    """Return ``(repo, number)`` parsed from ``task`` or raise ``ValueError``."""
    for pattern in _PR_REF_PATTERNS:
        m = pattern.search(task)
        if not m:
            continue
        groups = m.groups()
        if groups[0].isdigit():
            return groups[1], int(groups[0])
        return groups[0], int(groups[1])
    raise ValueError(
        "impossible d'extraire la PR depuis la tâche. "
        "Formats supportés : `owner/repo#N`, "
        "`https://github.com/owner/repo/pull/N`, `PR #N of owner/repo`."
    )


# === Langfuse callbacks (same defensive pattern as dev.py) ===


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


# === Structured output schema (internal, sans le champ `perspective`) ===


class _Assessment(BaseModel):
    """Schema asked to the LLM. ``perspective`` is added by the node itself."""

    findings: str = Field(..., min_length=1, description="Constat en markdown court.")
    severity: Severity = Field(..., description="block | warn | info")


# === Nodes ===


def prepare(state: ReviewerState) -> dict:
    """Parse PR ref + fetch diff once. Single source of truth for the 3 perspectives."""
    repo, number = _parse_pr_ref(state.task)
    diff = gh_pr_diff.invoke({"repo": repo, "number": number})
    return {"repo": repo, "pr_number": number, "diff": diff}


def fan_out(state: ReviewerState) -> list[Send]:
    """Send the prepared state to each perspective node in parallel."""
    return [Send(f"assess_{p}", state) for p in PERSPECTIVES]


def _assess(perspective: Perspective, diff: str, task: str) -> PerspectiveOpinion:
    """One perspective call. Diff is sent with ``cache_control: ephemeral``
    so the second and third calls hit the cache."""
    role_skill = load_skills([PERSPECTIVE_SKILLS[perspective]])

    system_blocks = [
        {"type": "text", "text": REVIEWER_SYSTEM_PREFIX},
        {
            "type": "text",
            "text": diff or "(diff vide)",
            "cache_control": {"type": "ephemeral"},
        },
    ]
    system = SystemMessage(content=system_blocks)
    human = HumanMessage(
        content=(
            f"Tâche utilisateur : {task}\n\n"
            f"Applique la perspective `{perspective}` selon ces règles :\n\n"
            f"{role_skill}"
        )
    )

    llm = ChatAnthropic(model=MODEL, max_tokens=1024).with_structured_output(_Assessment)
    try:
        result: _Assessment = llm.invoke(
            [system, human],
            config={
                "callbacks": _LANGFUSE_CALLBACKS,
                "run_name": f"reviewer_{perspective}",
            },
        )
        return PerspectiveOpinion(
            perspective=perspective,
            findings=result.findings,
            severity=result.severity,
        )
    except Exception as exc:
        logger.warning("perspective %s failed: %s", perspective, exc)
        return PerspectiveOpinion(
            perspective=perspective,
            findings=f"erreur LLM ({type(exc).__name__}) — perspective ignorée.",
            severity="info",
        )


def _make_perspective_node(perspective: Perspective):
    def node(state: ReviewerState) -> dict:
        opinion = _assess(perspective, state.diff, state.task)
        return {"perspectives": [opinion]}

    node.__name__ = f"assess_{perspective}"
    return node


def synthesize(state: ReviewerState) -> dict:
    """Combine the 3 opinions into a markdown response, ordered by severity."""
    sorted_ops = sorted(state.perspectives, key=lambda o: SEVERITY_ORDER[o.severity])

    parts = [f"# Review {state.repo}#{state.pr_number}", ""]
    for op in sorted_ops:
        parts.append(f"## {op.perspective.capitalize()} — `{op.severity}`")
        parts.append("")
        parts.append(op.findings.strip())
        parts.append("")
    return {"response": "\n".join(parts).rstrip() + "\n"}


def build_reviewer_graph():
    graph = StateGraph(ReviewerState)
    graph.add_node("prepare", prepare)
    for p in PERSPECTIVES:
        graph.add_node(f"assess_{p}", _make_perspective_node(p))
    graph.add_node("synthesize", synthesize)

    graph.add_edge(START, "prepare")
    graph.add_conditional_edges(
        "prepare",
        fan_out,
        [f"assess_{p}" for p in PERSPECTIVES],
    )
    for p in PERSPECTIVES:
        graph.add_edge(f"assess_{p}", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


def reviewer_metadata(perspectives: list[PerspectiveOpinion]) -> dict:
    """Metadata exposed via ``AgentResponse.metadata`` for the reviewer endpoint."""
    return {
        "severities": {op.perspective: op.severity for op in perspectives},
        "perspectives_count": len(perspectives),
    }
