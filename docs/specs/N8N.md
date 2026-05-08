# N8N.md — Workflows automatisés

_Source de vérité pour les workflows n8n de KisnLab._

---

## Rôle de n8n dans la stack

n8n gère les **automatisations déterministes** : CRON, webhooks, règles fixes.
Il se distingue d'OpenClaw (conversationnel) — chacun dans son paradigme, pas de doublon.

OpenClaw ↔ n8n communiquent par **webhooks HTTP** internes.

---

## Accès

- URL : `http://n8n.kisnlab.local`
- Auth : `N8N_USER` / `N8N_PASSWORD` (basicauth)
- Mode d'exécution : `queue` (via Redis)
- Timezone : `Europe/Paris`

---

## Exports versionnés

Les workflows exportés sont stockés dans `workflows/` à la racine du projet.
Nommage : `[pole]-[action].json`
Exemples : `admin-relance-factures.json`, `dev-brief-hebdo.json`

> `workflows/exports/` est dans `.gitignore` — seuls les exports finaux validés vont dans `workflows/`.

---

## Workflows actifs

| Workflow | Trigger | Action | Channel cible |
|----------|---------|--------|--------------|
| `strategie-publier-veille` | CRON `30 9 * * *` (9h30 7/7, Europe/Paris) | Fetch RSS multi-sources (33 flux : IA, Dev, Business-FR, Sécu, X via RSSHub) sur fenêtre 24h glissantes → POST webhook OpenClaw → skill `strategie-veille` synthétise un digest narratif | `#strategie` |

---

## Backlog — Workflows à créer

### Priorité 1

| Workflow | Trigger | Action | Channel cible |
|----------|---------|--------|--------------|
| Brief hebdomadaire | CRON lundi 9h | Résumé des 5 projets actifs via OpenClaw | `#briefs` |
| Relance factures | CRON quotidien 9h | Vérifier factures > 30j → alerte | `#alertes` / `#admin` |

### Priorité 2

| Workflow | Trigger | Action | Channel cible |
|----------|---------|--------|--------------|
| Résumé coûts LLM | CRON vendredi 17h | Récupérer stats Langfuse → résumé | `#logs` |
| Alerte erreur critique | Webhook Langfuse | Filtrer erreurs sévères → notifier | `#alertes` |

### Priorité 3 (backlog)

| Workflow | Trigger | Action | Channel cible |
|----------|---------|--------|--------------|
| Rapport mensuel SASU | CRON 1er du mois | Synthèse activité + CA estimé | `#admin` |

---

## Connexions configurées dans n8n

| Service | Type | Notes |
|---------|------|-------|
| Postgres | Database | BDD `n8n` sur `kisnlab-postgres` |
| Redis | Queue | `kisnlab-redis:6379` |
| Discord | Bot | Via `DISCORD_BOT_TOKEN` |
| OpenClaw | Webhook | `http://kisnlab-openclaw:18789/plugins/webhooks/n8n` (Bearer `OPENCLAW_WEBHOOK_SECRET`, exposé à n8n via env compose) |
| RSSHub | HTTP | `http://kisnlab-rsshub:1200` (interne, sources X/Twitter, GitHub trending, Anthropic news, OpenAI blog) |
| Langfuse | HTTP | `http://langfuse:3000` (interne) |

> ⚠️ Convention DNS interne : utiliser le **nom du container** (`kisnlab-<service>`) et pas le service name Compose pour les URLs inter-containers. Le service name ne résout pas systématiquement (constaté pour `openclaw` depuis n8n, 2026-04-26).

---

## Convention de nommage des workflows

```
[pole]-[action]
  pole   : admin, dev, commercial, comm, strategie, infra
  action : verbe court à l'infinitif

Exemples :
  admin-relancer-factures
  dev-generer-brief
  infra-alerter-erreurs
  comm-publier-linkedin
```

---

## Notes importantes

- `N8N_ENCRYPTION_KEY` : **ne jamais changer** après le 1er lancement (les credentials stockés deviendraient illisibles)
- Les webhooks internes passent par le réseau Docker (`http://openclaw:18789`) — pas par Traefik
- Exporter les workflows validés avant toute mise à jour d'image n8n
