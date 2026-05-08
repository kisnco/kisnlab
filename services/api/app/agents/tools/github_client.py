"""Authenticated GitHub REST client scoped to PR read + review operations.

Read-only on the working tree: no clone, no checkout, no push. PRs are reviewed
through the GitHub API surface only. ``gh_pr_create`` / ``git_push`` will be
added in a later iteration when an agent actually needs to ship code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import httpx

from .github_app import GITHUB_API_BASE, InstallationTokenProvider

ReviewEvent = Literal["APPROVE", "REQUEST_CHANGES", "COMMENT"]


@dataclass(frozen=True)
class PullRequestSummary:
    number: int
    title: str
    author: str
    state: str
    head_ref: str
    base_ref: str
    url: str


@dataclass(frozen=True)
class PullRequestDetails:
    number: int
    title: str
    body: str
    author: str
    state: str
    head_ref: str
    base_ref: str
    url: str
    additions: int
    deletions: int
    changed_files: int


class GitHubClient:
    def __init__(
        self,
        token_provider: InstallationTokenProvider,
        *,
        timeout: float = 15.0,
    ) -> None:
        self._token_provider = token_provider
        self._timeout = timeout

    def _headers(self, *, accept: str = "application/vnd.github+json") -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token_provider.get_token()}",
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        accept: str = "application/vnd.github+json",
    ) -> httpx.Response:
        url = f"{GITHUB_API_BASE}{path}"
        response = httpx.request(
            method,
            url,
            headers=self._headers(accept=accept),
            json=json,
            timeout=self._timeout,
        )
        response.raise_for_status()
        return response

    def list_prs(
        self,
        repo: str,
        *,
        state: Literal["open", "closed", "all"] = "open",
        limit: int = 30,
    ) -> list[PullRequestSummary]:
        response = self._request(
            "GET",
            f"/repos/{repo}/pulls?state={state}&per_page={limit}",
        )
        return [_to_summary(item) for item in response.json()]

    def get_pr(self, repo: str, number: int) -> PullRequestDetails:
        response = self._request("GET", f"/repos/{repo}/pulls/{number}")
        return _to_details(response.json())

    def get_pr_diff(self, repo: str, number: int) -> str:
        response = self._request(
            "GET",
            f"/repos/{repo}/pulls/{number}",
            accept="application/vnd.github.v3.diff",
        )
        return response.text

    def review_pr(
        self,
        repo: str,
        number: int,
        *,
        event: ReviewEvent,
        body: str,
    ) -> dict[str, Any]:
        response = self._request(
            "POST",
            f"/repos/{repo}/pulls/{number}/reviews",
            json={"event": event, "body": body},
        )
        return response.json()

    def comment_pr(self, repo: str, number: int, body: str) -> dict[str, Any]:
        response = self._request(
            "POST",
            f"/repos/{repo}/issues/{number}/comments",
            json={"body": body},
        )
        return response.json()


def _to_summary(item: dict[str, Any]) -> PullRequestSummary:
    return PullRequestSummary(
        number=item["number"],
        title=item["title"],
        author=item.get("user", {}).get("login", ""),
        state=item["state"],
        head_ref=item.get("head", {}).get("ref", ""),
        base_ref=item.get("base", {}).get("ref", ""),
        url=item.get("html_url", ""),
    )


def _to_details(item: dict[str, Any]) -> PullRequestDetails:
    return PullRequestDetails(
        number=item["number"],
        title=item["title"],
        body=item.get("body") or "",
        author=item.get("user", {}).get("login", ""),
        state=item["state"],
        head_ref=item.get("head", {}).get("ref", ""),
        base_ref=item.get("base", {}).get("ref", ""),
        url=item.get("html_url", ""),
        additions=item.get("additions", 0),
        deletions=item.get("deletions", 0),
        changed_files=item.get("changed_files", 0),
    )
