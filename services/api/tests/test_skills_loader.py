"""``load_skills`` reads markdown fragments from ``app/agents/skills``."""

import pytest

from app.agents.skills import load_skills


def test_load_single_skill_returns_content():
    out = load_skills(["dev_base"])
    assert "agent dev de KisnLab" in out


def test_load_multiple_skills_joins_with_separator():
    out = load_skills(["dev_base", "github_pr_tools"])
    assert "\n\n---\n\n" in out
    assert "gh_pr_diff" in out
    assert "agent dev de KisnLab" in out


def test_preserves_order():
    out = load_skills(["github_pr_tools", "dev_base"])
    head, _, tail = out.partition("\n\n---\n\n")
    assert "Outils GitHub" in head
    assert "agent dev de KisnLab" in tail


def test_missing_skill_raises():
    with pytest.raises(FileNotFoundError):
        load_skills(["does_not_exist"])


@pytest.mark.parametrize("bad", ["", ".hidden", "sub/dir"])
def test_invalid_name_raises(bad: str):
    with pytest.raises(ValueError):
        load_skills([bad])
