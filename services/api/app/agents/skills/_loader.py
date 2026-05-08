"""Tiny markdown skill loader (Phase 1).

```python
from app.agents.skills import load_skills

prompt = load_skills(["dev_base", "github_pr_tools"])
```

- Lookup directory: ``services/api/app/agents/skills/<name>.md``.
- Returns a single string with fragments joined by ``\\n\\n---\\n\\n``.
- Missing files raise ``FileNotFoundError`` immediately (fail fast at boot).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

_SKILLS_DIR = Path(__file__).parent
_SEPARATOR = "\n\n---\n\n"


def _resolve(name: str) -> Path:
    if not name or "/" in name or name.startswith("."):
        raise ValueError(f"invalid skill name: {name!r}")
    path = _SKILLS_DIR / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"skill not found: {path}")
    return path


def load_skills(names: Iterable[str]) -> str:
    """Return the concatenated markdown for the given skill names.

    Order is preserved. Each fragment is stripped of trailing whitespace
    before joining so the separator stays clean.
    """
    fragments = [_resolve(n).read_text(encoding="utf-8").rstrip() for n in names]
    return _SEPARATOR.join(fragments)
