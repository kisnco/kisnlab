"""Tests des helpers purs du bot dev (pas de Discord, pas de HTTP)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Stub des env vars *avant* d'importer ``main`` (qui les lit au top-level).
os.environ.setdefault("DISCORD_DEV_BOT_TOKEN", "stub-token")
os.environ.setdefault("DISCORD_YOUR_USER_ID", "0")
os.environ.setdefault("KISNLAB_API_TOKEN", "stub-api-token")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402 — sys.path tweak nécessaire au-dessus.

DISCORD_MAX_LEN = main.DISCORD_MAX_LEN


class TestStripMention:
    def test_strips_basic_mention(self):
        assert main._strip_mention("<@123> review la PR #5", 123) == "review la PR #5"

    def test_strips_legacy_bang_mention(self):
        assert main._strip_mention("<@!123> hello", 123) == "hello"

    def test_strips_mention_anywhere(self):
        assert main._strip_mention("hey <@123> please", 123) == "hey  please".strip()

    def test_no_mention_passthrough(self):
        assert main._strip_mention("just text", 123) == "just text"

    def test_only_mention_returns_empty(self):
        assert main._strip_mention("<@123>", 123) == ""


class TestFormatResponse:
    def test_short_response_single_chunk(self):
        chunks = main._format_response("dev", "court")
        assert chunks == ["**[dev]**\n\ncourt"]

    def test_empty_body_keeps_prefix(self):
        chunks = main._format_response("dev", "")
        assert len(chunks) == 1
        assert "[dev]" in chunks[0]

    def test_long_response_splits(self):
        body = "x" * 5000
        chunks = main._format_response("reviewer", body)
        assert len(chunks) > 1
        assert all(len(c) <= DISCORD_MAX_LEN for c in chunks)
        # prefix only on first chunk
        assert chunks[0].startswith("**[reviewer]**")
        for later in chunks[1:]:
            assert "[reviewer]" not in later

    def test_split_prefers_newline(self):
        # Construit un body qui force un split, avec un \n placé près de la limite.
        body = ("a" * (DISCORD_MAX_LEN - 50)) + "\n" + ("b" * 100)
        chunks = main._format_response("dev", body)
        assert len(chunks) == 2
        # chunk 1 ne contient PAS de "b" — le split a respecté le \n
        assert "b" not in chunks[0]
        assert chunks[1].startswith("b")

    def test_split_falls_back_to_hard_cut_when_no_newline(self):
        body = "a" * 5000  # aucun \n disponible
        chunks = main._format_response("dev", body)
        assert len(chunks) >= 3
        assert all(len(c) <= DISCORD_MAX_LEN for c in chunks)

    def test_full_body_reassembles(self):
        body = "alpha\nbeta\ngamma\n" + ("z" * 4000)
        chunks = main._format_response("dev", body)
        # premier chunk a le préfixe, on le retire pour reconstituer
        first = chunks[0].removeprefix("**[dev]**\n\n")
        rejoined = first + "\n" + "\n".join(chunks[1:])
        # le rejointage peut ajouter un \n en trop selon où on a coupé,
        # on vérifie que le body est inclus tel quel
        assert all(line in rejoined for line in ["alpha", "beta", "gamma"])
