# KisnLab — Claude Code

## Qui je suis

**Développeuse senior & responsable technique — KIS'n Code**
Profil hybride : architecte technique · lead dev · accélératrice de projets

**Expertise principale**
- Symfony, API-first, Docker, CI/CD, sécurité (ISO 27001, SSO, auth)
- Refonte legacy · architecture scalable · pipelines CI/CD
- Vision produit + exécution technique

**Langages** : PHP/Symfony (fort) › JS/TS (fort) › Python (en apprentissage)
**Stack** : Symfony, React/Next.js, Tailwind, Docker, Postgres

**Philosophie** : _Keep It Simple, Make It Work_
→ Simplicité · Impact · Maîtrise — moins de complexité, plus de résultats.

---

## KIS'n Code

Boîte de développement & conseil.
**Clients** : TPE/PME, collectivités, porteurs de projets
**Offre** : dev sur mesure · refonte technique · archi propre · conseil structurant

---

## KisnLab

Stack IA auto-hébergée pour piloter KIS'n Code depuis Discord.
**Lire `docs/specs/` avant toute action.**

### Stack active (2026-05-08)

| Service | Image | Accès |
|---------|-------|-------|
| Traefik | traefik:v3.2 | http://traefik.kisnlab.local |
| Postgres+pgvector | pgvector/pgvector:pg16 | port 5432 (interne) |
| Redis | redis:7-alpine | port 6379 (interne) |
| OpenClaw | alpine/openclaw:2026.4.15 | http://openclaw.kisnlab.local:18789 |
| n8n | n8nio/n8n:latest | http://n8n.kisnlab.local |
| ClickHouse | clickhouse/clickhouse-server:24.12 | port 8123 (interne) |
| Langfuse v3 | langfuse/langfuse:3 | http://langfuse.kisnlab.local |
| KisnLab API | python:3.12-slim (build local) | http://api.kisnlab.local |

### Faits importants sur OpenClaw

- Config active : `OPENCLAW_STATE_DIR=/workspace` → lit `/workspace/openclaw.json`
- Le vrai schéma est strict — toujours utiliser `openclaw config set` plutôt qu'éditer le JSON à la main
- Auth-profiles stocké dans `config/openclaw/agents/` (gitignore, contient la clé API)
- Modèle actif : `anthropic/claude-haiku-4-5-20251001` (claude-opus-4-7 indisponible sur le tier actuel)
- Discord configuré via guilds allowlist — `requireMention: false`
- Plugin webhooks activé sur `/plugins/webhooks/n8n` (secret via `OPENCLAW_WEBHOOK_SECRET`)

---

## Règles absolues

1. Lire le spec concerné dans `docs/specs/` avant de toucher à quoi que ce soit
2. Mettre à jour le spec + `CHANGELOG.md` après chaque modification significative
3. Ne jamais afficher ni lire `.env`
4. Ne jamais modifier `docker-compose.yml` ou `openclaw.json` sans montrer le diff d'abord
5. Toujours demander si c'est ambigu — une question vaut mieux qu'une erreur
6. Rester minimal : la solution la plus simple qui marche

---

## Ma méthode de travail

```
1. Lire le spec → comprendre le contexte
2. Proposer avant d'agir (si impact important)
3. Faire → minimal, fonctionnel, lisible
4. Mettre à jour le spec + CHANGELOG
```

**Priorités** : ça marche › ça ne casse rien › c'est lisible › c'est élégant

---

## Conventions

- Code en **anglais**, messages UI/Discord en **français**
- Indentation **2 espaces** partout
- Containers : préfixe `kisnlab-`
- Skills OpenClaw : frontmatter YAML + `approval: required` si envoi externe
- Workflows n8n : nommage `[pole]-[action]`

---

## docs/specs/ — La source de vérité

Mis à jour **à chaque modification** du composant concerné.

```
docs/specs/
├── STACK.md          → services Docker, ports, dépendances
├── DISCORD.md        → serveur, channels, bot, permissions
├── OPENCLAW.md       → config, skills, routing LLM, heartbeat
├── OPENCLAW_API.md   → API gateway, webhooks, MCP (résultat spike)
├── N8N.md            → workflows actifs, triggers, webhooks
├── DATABASE.md       → schéma Postgres, tables, pgvector
├── SKILLS.md         → liste des skills, rôles, LLM assigné
├── PROJETS.md        → projets actifs et leur état
└── CHANGELOG.md      → historique de toutes les modifications
```

---

## Commandes utiles

```bash
# Stack
docker compose up -d
docker compose logs -f [service]
docker compose restart [service]
bash scripts/preflight.sh

# Postgres
docker exec -it kisnlab-postgres psql -U kisnlab_admin -d kisnlab_main

# OpenClaw config
docker exec kisnlab-openclaw openclaw config get [path]
docker exec kisnlab-openclaw openclaw config set [path] [value]
docker exec kisnlab-openclaw openclaw models list

# Backup
bash scripts/backup-postgres.sh
```
