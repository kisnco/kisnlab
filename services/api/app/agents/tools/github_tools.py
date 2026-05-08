"""LangChain ``@tool`` wrappers around :class:`GitHubClient`.

The agent receives plain strings (LLM-friendly) rather than dataclasses so
that observation chunks stay copy-pasteable into reviews.
"""

from __future__ import annotations

import json
import os
from typing import Literal

from langchain_core.tools import tool

from .github_app import DEFAULT_APP_NAME, InstallationTokenProvider
from .github_client import GitHubClient, ReviewEvent

DIFF_TRUNCATE_CHARS = 60_000  # keep tool observations within Claude's context budget

_token_provider: InstallationTokenProvider | None = None
_client: GitHubClient | None = None


def _get_client() -> GitHubClient:
    global _token_provider, _client
    if _client is None:
        app_name = os.getenv("GH_APP_NAME", DEFAULT_APP_NAME)
        _token_provider = InstallationTokenProvider(app_name)
        _client = GitHubClient(_token_provider)
    return _client


def reset_client_for_tests() -> None:
    """Clear the module-level singleton so tests can inject a fresh stub."""
    global _token_provider, _client
    _token_provider = None
    _client = None


@tool
def gh_pr_list(repo: str, state: Literal["open", "closed", "all"] = "open") -> str:
    """Lister les pull requests d'un repo GitHub (`owner/repo`).

    Args:
        repo: ex. ``kisnco/kisnlab``.
        state: ``open`` (defaut), ``closed`` ou ``all``.
    """
    prs = _get_client().list_prs(repo, state=state)
    if not prs:
        return f"Aucune PR ({state}) sur {repo}."
    lines = [
        f"#{p.number} [{p.state}] {p.title} — @{p.author} ({p.head_ref} → {p.base_ref})"
        for p in prs
    ]
    return "\n".join(lines)


@tool
def gh_pr_get(repo: str, number: int) -> str:
    """Recuperer les metadonnees d'une PR : titre, auteur, base/head, taille, body."""
    pr = _get_client().get_pr(repo, number)
    payload = {
        "number": pr.number,
        "title": pr.title,
        "author": pr.author,
        "state": pr.state,
        "head": pr.head_ref,
        "base": pr.base_ref,
        "url": pr.url,
        "additions": pr.additions,
        "deletions": pr.deletions,
        "changed_files": pr.changed_files,
        "body": pr.body,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


@tool
def gh_pr_diff(repo: str, number: int) -> str:
    """Recuperer le diff unifie d'une PR. Tronque a 60k caracteres si necessaire."""
    diff = _get_client().get_pr_diff(repo, number)
    if len(diff) > DIFF_TRUNCATE_CHARS:
        return diff[:DIFF_TRUNCATE_CHARS] + f"\n... [tronque, total {len(diff)} chars]"
    return diff


@tool
def gh_pr_review(
    repo: str,
    number: int,
    event: ReviewEvent,
    body: str,
) -> str:
    """Poster une review sur une PR.

    Args:
        repo: ``owner/repo``.
        number: numero de la PR.
        event: ``APPROVE``, ``REQUEST_CHANGES`` ou ``COMMENT``.
        body: contenu de la review (markdown).
    """
    result = _get_client().review_pr(repo, number, event=event, body=body)
    return f"Review postee (id={result.get('id')}, state={result.get('state')})."


@tool
def gh_pr_comment(repo: str, number: int, body: str) -> str:
    """Poster un commentaire simple (issue comment) sur une PR."""
    result = _get_client().comment_pr(repo, number, body)
    return f"Commentaire poste (id={result.get('id')})."


GITHUB_PR_TOOLS = [gh_pr_list, gh_pr_get, gh_pr_diff, gh_pr_review, gh_pr_comment]
