"""Unit tests for github_client: PR list/get/diff/review/comment via httpx mock."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.agents.tools import github_client
from app.agents.tools.github_app import InstallationTokenProvider


@pytest.fixture
def fake_provider():
    provider = MagicMock(spec=InstallationTokenProvider)
    provider.get_token.return_value = "ghs_test_token"
    return provider


@pytest.fixture
def client(fake_provider):
    return github_client.GitHubClient(fake_provider)


def _http_response(status: int = 200, json_body: object = None, text: str = "") -> MagicMock:
    response = MagicMock(spec=httpx.Response)
    response.status_code = status
    if json_body is not None:
        response.json.return_value = json_body
    response.text = text
    response.raise_for_status.return_value = None
    return response


def test_list_prs_parses_summaries(client):
    payload = [
        {
            "number": 12,
            "title": "feat: foo",
            "state": "open",
            "user": {"login": "alice"},
            "head": {"ref": "feat/foo"},
            "base": {"ref": "main"},
            "html_url": "https://github.com/x/y/pull/12",
        }
    ]
    with patch.object(github_client.httpx, "request", return_value=_http_response(json_body=payload)) as req:
        result = client.list_prs("x/y", state="open", limit=10)
        assert len(result) == 1
        pr = result[0]
        assert pr.number == 12
        assert pr.title == "feat: foo"
        assert pr.author == "alice"
        assert pr.head_ref == "feat/foo"
        assert pr.base_ref == "main"
        # Auth header carries the bot token
        assert req.call_args.kwargs["headers"]["Authorization"] == "Bearer ghs_test_token"


def test_get_pr_parses_details(client):
    payload = {
        "number": 7,
        "title": "fix: bar",
        "body": "fixes #1",
        "state": "open",
        "user": {"login": "bob"},
        "head": {"ref": "fix/bar"},
        "base": {"ref": "main"},
        "html_url": "https://github.com/x/y/pull/7",
        "additions": 10,
        "deletions": 3,
        "changed_files": 2,
    }
    with patch.object(github_client.httpx, "request", return_value=_http_response(json_body=payload)):
        pr = client.get_pr("x/y", 7)
        assert pr.number == 7
        assert pr.body == "fixes #1"
        assert pr.additions == 10
        assert pr.changed_files == 2


def test_get_pr_diff_returns_raw_text(client):
    diff_text = "diff --git a/foo b/foo\n--- a/foo\n+++ b/foo\n"
    with patch.object(
        github_client.httpx,
        "request",
        return_value=_http_response(text=diff_text),
    ) as req:
        result = client.get_pr_diff("x/y", 7)
        assert result == diff_text
        # Diff requires the v3.diff Accept header
        assert req.call_args.kwargs["headers"]["Accept"] == "application/vnd.github.v3.diff"


def test_review_pr_posts_event_and_body(client):
    with patch.object(
        github_client.httpx,
        "request",
        return_value=_http_response(json_body={"id": 999, "state": "APPROVED"}),
    ) as req:
        result = client.review_pr("x/y", 7, event="APPROVE", body="LGTM")
        assert result["id"] == 999
        kwargs = req.call_args.kwargs
        assert kwargs["json"] == {"event": "APPROVE", "body": "LGTM"}
        assert req.call_args.args[0] == "POST"


def test_comment_pr_uses_issues_endpoint(client):
    with patch.object(
        github_client.httpx,
        "request",
        return_value=_http_response(json_body={"id": 888}),
    ) as req:
        result = client.comment_pr("x/y", 7, "noted")
        assert result["id"] == 888
        # Issue comments endpoint, not pulls
        assert "/repos/x/y/issues/7/comments" in req.call_args.args[1]


def test_request_raises_on_http_error(client):
    error_response = MagicMock(spec=httpx.Response)
    error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "boom", request=MagicMock(), response=MagicMock()
    )
    with patch.object(github_client.httpx, "request", return_value=error_response):
        with pytest.raises(httpx.HTTPStatusError):
            client.list_prs("x/y")
