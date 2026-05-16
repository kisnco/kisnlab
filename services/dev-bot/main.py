"""KisnLab Dev Team — bot Discord.

Écoute les mentions du seul utilisateur autorisé et transmet chaque tâche à
``POST /agents/team/run`` (le superviseur LangGraph route ensuite vers ``dev``
ou ``reviewer``). Aucune logique métier ici — pure plomberie Discord ↔ HTTP.
"""

from __future__ import annotations

import logging
import os

import discord
import httpx

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("dev-bot")

DISCORD_TOKEN = os.environ["DISCORD_DEV_BOT_TOKEN"]
ALLOWED_USER_ID = int(os.environ["DISCORD_YOUR_USER_ID"])
API_URL = os.environ.get("KISNLAB_API_URL", "http://kisnlab-api:8000").rstrip("/")
API_TOKEN = os.environ["KISNLAB_API_TOKEN"]

DISCORD_MAX_LEN = 2000
HTTP_TIMEOUT = 120.0  # le reviewer fait 3 LLM calls parallèles, ~30-60s

# Messages d'erreur user-friendly mappés aux codes HTTP qu'on peut rencontrer.
ERROR_MESSAGES = {
    401: "⚠️ Auth API échouée — token mal configuré côté bot.",
    422: "⚠️ Tâche non comprise (souvent : référence de PR introuvable).",
    503: "⚠️ Service indisponible — l'API n'est pas prête.",
}


def _strip_mention(content: str, bot_id: int) -> str:
    """Retire les patterns `<@bot_id>` et `<@!bot_id>` (legacy)."""
    return content.replace(f"<@{bot_id}>", "").replace(f"<@!{bot_id}>", "").strip()


def _format_response(routed_to: str, body: str) -> list[str]:
    """Découpe la réponse en chunks Discord-compatibles (≤ 2000 chars).

    Le préfixe ``[<routed_to>]`` apparaît uniquement sur le premier chunk.
    Coupe en priorité sur un saut de ligne pour ne pas trancher au milieu
    d'un mot.
    """
    prefix = f"**[{routed_to}]**\n\n"
    if len(prefix) + len(body) <= DISCORD_MAX_LEN:
        return [prefix + body] if body else [prefix.rstrip()]

    chunks: list[str] = []
    remaining = body
    is_first = True
    while remaining:
        budget = DISCORD_MAX_LEN - (len(prefix) if is_first else 0)
        if len(remaining) <= budget:
            chunk_body = remaining
            remaining = ""
        else:
            chunk_body = remaining[:budget]
            # Préférer une coupe sur un saut de ligne dans les 200 derniers chars.
            nl = chunk_body.rfind("\n", max(0, budget - 200))
            if nl > 0:
                chunk_body = remaining[:nl]
                remaining = remaining[nl + 1 :]
            else:
                remaining = remaining[budget:]
        chunks.append((prefix + chunk_body) if is_first else chunk_body)
        is_first = False
    return chunks


# --- Discord client ---

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready() -> None:
    logger.info("connected as %s (id=%s)", client.user, client.user.id)


@client.event
async def on_message(message: discord.Message) -> None:
    if message.author == client.user:
        return  # jamais répondre à soi-même
    if message.author.id != ALLOWED_USER_ID:
        return  # allowlist stricte (cohérent avec OpenClaw)
    if client.user not in message.mentions:
        return  # déclenche uniquement sur mention explicite

    task = _strip_mention(message.content, client.user.id)
    if not task:
        await message.reply(
            "Mentionne-moi avec une tâche : `@KisnLab Dev Team review la PR #N de owner/repo`."
        )
        return

    logger.info("task from %s (channel=%s): %s", message.author, message.channel, task[:120])

    async with message.channel.typing():
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http:
                resp = await http.post(
                    f"{API_URL}/agents/team/run",
                    json={"task": task},
                    headers={"Authorization": f"Bearer {API_TOKEN}"},
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            base = ERROR_MESSAGES.get(exc.response.status_code, f"⚠️ API {exc.response.status_code}")
            detail = exc.response.text[:300]
            await message.reply(f"{base}\n```\n{detail}\n```")
            return
        except httpx.TimeoutException:
            await message.reply("⚠️ Timeout API (>120s) — vérifie les logs `kisnlab-api`.")
            return
        except Exception as exc:  # noqa: BLE001 — on remonte une trace lisible
            logger.exception("dev-bot dispatch failed")
            await message.reply(f"⚠️ {type(exc).__name__} : {exc}")
            return

    routed_to = data.get("metadata", {}).get("routed_to", "?")
    body = data.get("response", "(réponse vide)")
    chunks = _format_response(routed_to, body)
    for index, chunk in enumerate(chunks):
        if index == 0:
            await message.reply(chunk)
        else:
            await message.channel.send(chunk)


def main() -> None:
    client.run(DISCORD_TOKEN, log_handler=None)  # déjà configuré via logging.basicConfig


if __name__ == "__main__":
    main()
