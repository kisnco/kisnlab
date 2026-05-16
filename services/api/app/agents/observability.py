"""Observability — callback Langfuse partagé par tous les agents.

Pattern défensif identique : si les env vars manquent OU si l'import échoue
(lib absente / network), on retourne ``[]`` pour garder les agents
opérationnels sans observabilité.

La liste est construite **une seule fois** à l'import — singleton réutilisé
par ``dev.py``, ``reviewer.py`` et ``team.py``.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _build() -> list[Any]:
    if not (
        os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")
    ):
        return []
    try:
        from langfuse.langchain import CallbackHandler

        return [CallbackHandler()]
    except Exception as exc:  # noqa: BLE001 — on dégrade gracieusement
        logger.warning("Langfuse tracing disabled (callback unavailable): %s", exc)
        return []


LANGFUSE_CALLBACKS: list[Any] = _build()
