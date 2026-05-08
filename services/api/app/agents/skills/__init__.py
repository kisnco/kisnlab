"""Markdown skill fragments injected into agent system prompts.

Use ``app.agents.skills.load_skills([...])`` to compose a system prompt.
"""

from app.agents.skills._loader import load_skills

__all__ = ["load_skills"]
