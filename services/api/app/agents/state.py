"""Shared Pydantic contracts for the multi-agent dev team (Phase 1).

Two layers:

- **API boundary** (``AgentRequest`` / ``AgentResponse``): wire-compatible
  envelope used by every ``/agents/*/run`` endpoint.
- **Internal LangGraph states** (``DevState`` / ``ReviewerState`` / ``TeamState``):
  one Pydantic model per graph. LangGraph 0.2 accepts ``StateGraph(BaseModel)``;
  nodes may return either a full instance or a partial dict.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, Field


def read_field(result: Any, field: str) -> Any:
    """LangGraph state may be a dict or the BaseModel; normalize."""
    return result[field] if isinstance(result, dict) else getattr(result, field)

# === API boundary ===

AgentName = Literal["dev", "reviewer"]
ResponderName = Literal["dev", "reviewer", "team"]


class AgentRequest(BaseModel):
    """Single shape for every ``/agents/*/run`` endpoint."""

    task: str = Field(..., min_length=1, max_length=8000)


class AgentResponse(BaseModel):
    """``metadata`` carries agent-specific info:

    - ``team`` → ``{"routed_to": "dev" | "reviewer"}``
    - ``reviewer`` → ``{"severities": [...], "perspectives_count": 3}``
    """

    agent: ResponderName
    response: str
    metadata: dict = Field(default_factory=dict)


# === Internal LangGraph states ===


class DevState(BaseModel):
    task: str
    response: str = ""


Severity = Literal["block", "warn", "info"]
Perspective = Literal["security", "quality", "architecture"]


class PerspectiveOpinion(BaseModel):
    perspective: Perspective
    findings: str
    severity: Severity


class ReviewerState(BaseModel):
    task: str
    repo: Optional[str] = None
    pr_number: Optional[int] = None
    diff: str = ""
    # ``operator.add`` reducer merges parallel writes from the 3 perspective nodes.
    perspectives: Annotated[list[PerspectiveOpinion], operator.add] = Field(default_factory=list)
    response: str = ""


class TeamState(BaseModel):
    task: str
    routed_to: Optional[AgentName] = None
    response: str = ""
