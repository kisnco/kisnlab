"""Unit tests for the LangChain @tool wrappers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.agents.tools import github_tools
from app.agents.tools.github_client import (
    GitHubClient,
    PullRequestDetails,
    PullRequestSummary,
)


@pytest.fixture
def fake_client(monkeypatch):
    client = MagicMock(spec=GitHubClient)
    monkeypatch.setattr(github_tools, "_client", client)
    monkeypatch.setattr(github_tools, "_token_provider", MagicMock())
    yield client
    github_tools.reset_client_for_tests()


def test_gh_pr_list_formats_summaries(fake_client):
    fake_client.list_prs.return_value = [
        PullRequestSummary(
            number=1,
            title="feat: x",
            author="alice",
            state="open",
            head_ref="feat/x",
            base_ref="main",
            url="https://example.com/1",
        )
    ]
    result = github_tools.gh_pr_list.invoke({"repo": "kisnco/kisnlab", "state": "open"})
    assert "#1" in result
    assert "alice" in result
    assert "feat/x → main" in result
    fake_client.list_prs.assert_called_once_with("kisnco/kisnlab", state="open")


def test_gh_pr_list_returns_message_when_empty(fake_client):
    fake_client.list_prs.return_value = []
    result = github_tools.gh_pr_list.invoke({"repo": "kisnco/kisnlab"})
    assert "Aucune PR" in result


def test_gh_pr_get_returns_json(fake_client):
    fake_client.get_pr.return_value = PullRequestDetails(
        number=2,
        title="fix: y",
        body="body",
        author="bob",
        state="open",
        head_ref="fix/y",
        base_ref="main",
        url="https://example.com/2",
        additions=5,
        deletions=1,
        changed_files=1,
    )
    result = github_tools.gh_pr_get.invoke({"repo": "kisnco/kisnlab", "number": 2})
    assert '"number": 2' in result
    assert '"author": "bob"' in result


def test_gh_pr_diff_truncates_large_diff(fake_client, monkeypatch):
    monkeypatch.setattr(github_tools, "DIFF_TRUNCATE_CHARS", 50)
    fake_client.get_pr_diff.return_value = "x" * 200
    result = github_tools.gh_pr_diff.invoke({"repo": "kisnco/kisnlab", "number": 3})
    assert result.startswith("x" * 50)
    assert "tronque" in result


def test_gh_pr_review_returns_status(fake_client):
    fake_client.review_pr.return_value = {"id": 42, "state": "APPROVED"}
    result = github_tools.gh_pr_review.invoke(
        {"repo": "kisnco/kisnlab", "number": 4, "event": "APPROVE", "body": "LGTM"}
    )
    assert "id=42" in result
    assert "state=APPROVED" in result
    fake_client.review_pr.assert_called_once_with(
        "kisnco/kisnlab", 4, event="APPROVE", body="LGTM"
    )


def test_gh_pr_comment_returns_status(fake_client):
    fake_client.comment_pr.return_value = {"id": 7}
    result = github_tools.gh_pr_comment.invoke(
        {"repo": "kisnco/kisnlab", "number": 4, "body": "ok"}
    )
    assert "id=7" in result
    fake_client.comment_pr.assert_called_once_with("kisnco/kisnlab", 4, "ok")


def test_get_client_singleton_lazy(monkeypatch):
    github_tools.reset_client_for_tests()
    monkeypatch.setenv("GH_APP_NAME", "kisnlab-test-app")

    sentinel_provider = MagicMock()
    sentinel_client = MagicMock(spec=GitHubClient)

    monkeypatch.setattr(
        github_tools, "InstallationTokenProvider", lambda name: sentinel_provider
    )
    monkeypatch.setattr(github_tools, "GitHubClient", lambda provider: sentinel_client)

    first = github_tools._get_client()
    second = github_tools._get_client()
    assert first is sentinel_client
    assert first is second  # cached

    github_tools.reset_client_for_tests()
