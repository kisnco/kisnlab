"""Reviewer graph: prepare → 3 parallel perspectives → synthesize."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.reviewer import (
    PERSPECTIVES,
    REVIEWER_SYSTEM_PREFIX,
    _Assessment,
    _parse_pr_ref,
    build_reviewer_graph,
    reviewer_metadata,
    synthesize,
)
from app.agents.state import PerspectiveOpinion, ReviewerState
from app.main import app

client = TestClient(app)


# === PR ref parser ===


class TestParsePrRef:
    @pytest.mark.parametrize(
        "task, expected",
        [
            ("https://github.com/kisnco/kisnlab/pull/8", ("kisnco/kisnlab", 8)),
            ("kisnco/kisnlab#8", ("kisnco/kisnlab", 8)),
            ("review PR #8 of kisnco/kisnlab", ("kisnco/kisnlab", 8)),
            ("merci de regarder #42 dans owner/repo", ("owner/repo", 42)),
        ],
    )
    def test_parses_supported_formats(self, task, expected):
        assert _parse_pr_ref(task) == expected

    def test_raises_when_no_ref(self):
        with pytest.raises(ValueError):
            _parse_pr_ref("review the PR I just opened")


# === Synthesize ===


class TestSynthesize:
    def test_orders_by_severity_block_first(self):
        ops = [
            PerspectiveOpinion(perspective="quality", findings="ras", severity="info"),
            PerspectiveOpinion(perspective="security", findings="leak", severity="block"),
            PerspectiveOpinion(perspective="architecture", findings="meh", severity="warn"),
        ]
        out = synthesize(
            ReviewerState(task="t", repo="o/r", pr_number=1, diff="x", perspectives=ops)
        )
        text = out["response"]
        assert text.index("Security") < text.index("Architecture") < text.index("Quality")
        assert "# Review o/r#1" in text


class TestReviewerMetadata:
    def test_summarizes_severities_and_count(self):
        ops = [
            PerspectiveOpinion(perspective="security", findings="x", severity="block"),
            PerspectiveOpinion(perspective="quality", findings="y", severity="warn"),
        ]
        meta = reviewer_metadata(ops)
        assert meta["perspectives_count"] == 2
        assert meta["severities"] == {"security": "block", "quality": "warn"}


# === Full graph (mocked LLM and gh_pr_diff) ===


def _mock_llm_returning(severity: str = "info", findings: str = "ras"):
    structured = MagicMock()
    structured.invoke.return_value = _Assessment(findings=findings, severity=severity)  # type: ignore[arg-type]
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    return llm


class TestReviewerGraph:
    def test_runs_3_perspectives_and_synthesizes(self):
        with patch("app.agents.reviewer.gh_pr_diff") as mock_diff, patch(
            "app.agents.reviewer.ChatAnthropic"
        ) as mock_anth:
            mock_diff.invoke.return_value = "--- a/file.py\n+++ b/file.py\n+leak"
            mock_anth.return_value = _mock_llm_returning(severity="warn", findings="trouvé")

            graph = build_reviewer_graph()
            result = graph.invoke(ReviewerState(task="kisnco/kisnlab#7"))

            perspectives = (
                result["perspectives"] if isinstance(result, dict) else result.perspectives
            )
            response = result["response"] if isinstance(result, dict) else result.response

            assert {op.perspective for op in perspectives} == set(PERSPECTIVES)
            assert all(op.severity == "warn" for op in perspectives)
            assert "kisnco/kisnlab#7" in response
            mock_diff.invoke.assert_called_once_with({"repo": "kisnco/kisnlab", "number": 7})
            # 3 LLM clients (one per perspective) → caching is on the prompt, not the client.
            assert mock_anth.call_count == 3

    def test_passes_diff_with_cache_control(self):
        with patch("app.agents.reviewer.gh_pr_diff") as mock_diff, patch(
            "app.agents.reviewer.ChatAnthropic"
        ) as mock_anth:
            mock_diff.invoke.return_value = "DIFFCONTENT"
            llm = _mock_llm_returning()
            mock_anth.return_value = llm

            build_reviewer_graph().invoke(ReviewerState(task="o/r#1"))

            structured_invoke = llm.with_structured_output.return_value.invoke
            assert structured_invoke.call_count == 3
            for call in structured_invoke.call_args_list:
                messages = call.args[0]
                system = messages[0]
                assert isinstance(system.content, list)
                assert system.content[0]["text"] == REVIEWER_SYSTEM_PREFIX
                assert system.content[1]["text"] == "DIFFCONTENT"
                assert system.content[1]["cache_control"] == {"type": "ephemeral"}

    def test_distinct_run_name_per_perspective(self):
        with patch("app.agents.reviewer.gh_pr_diff") as mock_diff, patch(
            "app.agents.reviewer.ChatAnthropic"
        ) as mock_anth:
            mock_diff.invoke.return_value = "x"
            llm = _mock_llm_returning()
            mock_anth.return_value = llm

            build_reviewer_graph().invoke(ReviewerState(task="o/r#1"))

            structured_invoke = llm.with_structured_output.return_value.invoke
            run_names = sorted(call.kwargs["config"]["run_name"] for call in structured_invoke.call_args_list)
            assert run_names == [
                "reviewer_architecture",
                "reviewer_quality",
                "reviewer_security",
            ]

    def test_perspective_failure_falls_back_to_info(self):
        with patch("app.agents.reviewer.gh_pr_diff") as mock_diff, patch(
            "app.agents.reviewer.ChatAnthropic"
        ) as mock_anth:
            mock_diff.invoke.return_value = "x"
            failing = MagicMock()
            failing.invoke.side_effect = RuntimeError("anthropic 529")
            llm = MagicMock()
            llm.with_structured_output.return_value = failing
            mock_anth.return_value = llm

            result = build_reviewer_graph().invoke(ReviewerState(task="o/r#1"))
            perspectives = (
                result["perspectives"] if isinstance(result, dict) else result.perspectives
            )
            assert all(op.severity == "info" for op in perspectives)
            assert all("erreur LLM" in op.findings for op in perspectives)


# === Endpoint ===


class TestReviewerEndpoint:
    def test_run_reviewer_returns_metadata(self):
        with patch("app.routers.agents.reviewer_graph") as mock_graph:
            mock_graph.invoke.return_value = {
                "task": "o/r#1",
                "repo": "o/r",
                "pr_number": 1,
                "diff": "x",
                "perspectives": [
                    PerspectiveOpinion(perspective="security", findings="ok", severity="info"),
                    PerspectiveOpinion(perspective="quality", findings="ok", severity="warn"),
                    PerspectiveOpinion(
                        perspective="architecture", findings="ok", severity="block"
                    ),
                ],
                "response": "# Review",
            }

            res = client.post("/agents/reviewer/run", json={"task": "o/r#1"})
            assert res.status_code == 200
            body = res.json()
            assert body["agent"] == "reviewer"
            assert body["response"] == "# Review"
            assert body["metadata"]["perspectives_count"] == 3
            assert body["metadata"]["severities"]["security"] == "info"
            assert body["metadata"]["severities"]["architecture"] == "block"

    def test_invalid_pr_ref_returns_422(self):
        # We let the real graph parse and raise ValueError.
        res = client.post("/agents/reviewer/run", json={"task": "review please"})
        assert res.status_code == 422
        assert "PR" in res.json()["detail"]
