"""Contracts shared by every agent endpoint."""

import pytest
from pydantic import ValidationError

from app.agents.state import (
    AgentRequest,
    AgentResponse,
    DevState,
    PerspectiveOpinion,
    ReviewerState,
    TeamState,
)


class TestAgentRequest:
    def test_accepts_valid_task(self):
        req = AgentRequest(task="hello")
        assert req.task == "hello"

    def test_rejects_empty_task(self):
        with pytest.raises(ValidationError):
            AgentRequest(task="")

    def test_rejects_oversized_task(self):
        with pytest.raises(ValidationError):
            AgentRequest(task="x" * 8001)


class TestAgentResponse:
    def test_default_metadata_is_empty(self):
        resp = AgentResponse(agent="dev", response="ok")
        assert resp.metadata == {}

    def test_metadata_carries_team_route(self):
        resp = AgentResponse(agent="team", response="...", metadata={"routed_to": "dev"})
        assert resp.metadata["routed_to"] == "dev"

    def test_rejects_unknown_agent(self):
        with pytest.raises(ValidationError):
            AgentResponse(agent="unknown", response="ok")  # type: ignore[arg-type]


class TestInternalStates:
    def test_dev_state_default_response(self):
        s = DevState(task="t")
        assert s.response == ""

    def test_reviewer_state_starts_empty(self):
        s = ReviewerState(task="t")
        assert s.perspectives == []
        assert s.response == ""
        assert s.diff == ""
        assert s.repo is None
        assert s.pr_number is None

    def test_reviewer_state_carries_runtime_fields(self):
        s = ReviewerState(task="t", repo="kisnco/kisnlab", pr_number=8, diff="--- a/x")
        assert s.repo == "kisnco/kisnlab"
        assert s.pr_number == 8
        assert s.diff.startswith("---")

    def test_perspective_opinion_severity_enum(self):
        op = PerspectiveOpinion(perspective="security", findings="leak", severity="block")
        assert op.severity == "block"
        with pytest.raises(ValidationError):
            PerspectiveOpinion(perspective="security", findings="x", severity="nope")  # type: ignore[arg-type]

    def test_team_state_routed_to_optional(self):
        s = TeamState(task="t")
        assert s.routed_to is None
