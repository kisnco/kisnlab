# OPENCLAW_API.md — Spike technique : API et capacités réelles

_Résultat du spike d'inspection du container `alpine/openclaw:latest` — 2026-04-19_

---

## Image

- **Image** : `alpine/openclaw:latest`
- **Version** : `2026.4.15`
- **Runtime** : Node.js (ESM, `dist/index.js`)
- **Repo upstream** : https://github.com/openclaw/openclaw

---

## Gateway

- **Port interne** : `18789`
- **Exposé via Traefik** : `http://openclaw.kisnlab.local`
- **Protocol** : HTTP + WebSocket (`wss://`)

---

## Plugin Webhooks (intégration n8n)

### Activation dans `openclaw.json`

```json
"plugins": {
  "entries": {
    "webhooks": {
      "enabled": true,
      "config": {
        "routes": {
          "n8n": {
            "path": "/plugins/webhooks/n8n",
            "sessionKey": "agent:main:main",
            "secret": {
              "source": "env",
              "provider": "default",
              "id": "OPENCLAW_WEBHOOK_SECRET"
            },
            "description": "Bridge n8n → OpenClaw TaskFlow"
          }
        }
      }
    }
  }
}
```

### Appel depuis n8n

```bash
POST http://kisnlab-openclaw:18789/plugins/webhooks/n8n
Content-Type: application/json
Authorization: Bearer <OPENCLAW_WEBHOOK_SECRET>

{"action": "create_flow", "goal": "Génère le brief hebdomadaire KIS'n Code"}
```

### Actions disponibles

| Action | Description |
|--------|-------------|
| `create_flow` | Crée un TaskFlow avec un `goal` texte libre |
| `get_flow` | Lit l'état d'un TaskFlow existant |
| `list_flows` | Liste les TaskFlows actifs |
| `find_latest_flow` | Trouve le dernier TaskFlow |
| `resolve_flow` | Marque un flow comme résolu |
| `run_task` | Crée une tâche enfant dans un flow (`subagent` ou `acp`) |
| `resume_flow` | Reprend un flow en attente |
| `finish_flow` | Termine proprement un flow |
| `fail_flow` | Marque un flow comme échoué |
| `request_cancel` | Demande annulation |
| `cancel_flow` | Annule immédiatement |
| `get_task_summary` | Résumé d'une tâche |
| `set_waiting` | Met un flow en attente |

### Format de réponse

```json
// Succès
{ "ok": true, "routeId": "n8n", "result": {} }

// Erreur
{ "ok": false, "routeId": "n8n", "code": "not_found", "error": "TaskFlow not found.", "result": {} }
```

### Sécurité intégrée

- Auth par Bearer token (secret partagé via env `OPENCLAW_WEBHOOK_SECRET`)
- Rate limiting fenêtre fixe
- Limite de taille et timeout sur le body
- Limite de requêtes en vol simultanées

---

## MCP — Double rôle

### 1. OpenClaw comme serveur MCP (pour Claude Code)

`openclaw mcp serve` expose les conversations Discord via le protocole MCP.
Permet à Claude Code de lire/écrire dans les channels Discord directement.

```bash
# Depuis la machine hôte
openclaw mcp serve --url wss://openclaw.kisnlab.local --token-file ~/.openclaw/gateway.token
```

**Outils MCP exposés :**
`conversations_list` · `conversation_get` · `messages_read` · `attachments_fetch`
· `events_poll` · `events_wait` · `messages_send` · `permissions_list_open` · `permissions_respond`

### 2. OpenClaw comme client MCP (consomme des serveurs MCP)

Section `mcp.servers` dans `openclaw.json`. Permet aux runtimes OpenClaw
d'utiliser des MCP servers externes (filesystem, postgres, github, fetch…).

```json
"mcp": {
  "servers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://..."]
    }
  }
}
```

**Transports supportés :** `stdio` · `sse` · `streamable-http`

---

## Variables d'environnement requises (nouvelles)

| Variable | Usage | Obligatoire |
|----------|-------|-------------|
| `OPENCLAW_WEBHOOK_SECRET` | Secret partagé pour le plugin webhooks (n8n → OpenClaw) | Oui si webhooks activés |

Ajouter dans `.env` et passer au container `openclaw` dans `docker-compose.yml`.

---

## Décisions issues du spike

| # | Décision | Impact |
|---|----------|--------|
| D1 | Plugin webhooks à activer dans `openclaw.json` pour intégration n8n | Phase 3 |
| D2 | MCP client supporté — intégrer `filesystem` + `postgres` en Phase 4 | Phase 4 |
| D3 | Embeddings : `embeddingModel: "claude"` est invalide — désactiver en V1 (option A) | Phase 0 |
| D4 | `OPENCLAW_WEBHOOK_SECRET` à générer (`openssl rand -base64 32`) et ajouter dans `.env` | Phase 0 |

---

## Liens docs internes (dans le container)

- `/app/docs/plugins/webhooks.md` — plugin webhooks complet
- `/app/docs/cli/mcp.md` — MCP server + client registry
- `/app/docs/reference/rpc.md` — adaptateurs RPC (signal-cli, imsg)