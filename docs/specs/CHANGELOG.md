# CHANGELOG.md — Historique des modifications

_Toute modification significative de la stack, des configs ou des specs doit être loguée ici._

Format : `[YYYY-MM-DD] [composant] description`

---

## 2026-04-17

### Sécurité — docker-compose.yml
- Suppression de `--api.insecure=true` sur Traefik (dashboard non authentifié)
- Suppression du port `8080:8080` (dashboard Traefik plus exposé sur l'hôte)
- Ajout basicauth sur le router Traefik (`TRAEFIK_DASHBOARD_AUTH`)
- Suppression du port `5432:5432` (Postgres plus exposé sur l'hôte)
- `LANGFUSE_DEFAULT_PROJECT_ROLE` passé de `ADMIN` à `VIEWER`
- `.env.example` : ajout de `TRAEFIK_DASHBOARD_AUTH` avec instructions htpasswd

### Sécurité — init-multiple-dbs.sh
- Identifiants SQL (database, user) mis entre guillemets pour éviter l'injection

### Docs — docs/specs/
- Création initiale des 8 specs : `STACK.md`, `DISCORD.md`, `OPENCLAW.md`, `N8N.md`, `DATABASE.md`, `SKILLS.md`, `PROJETS.md`, `CHANGELOG.md`

---

## Avant 2026-04-17

### Architecture
- Validation de l'architecture finale (OpenClaw + n8n, rejet de CrewAI)
- Choix du LLM router : Sonnet (critiques) + Haiku (80% des appels)
- `docker-compose.yml` initial avec 6 services
- `.env.example` complet
- `config/openclaw/openclaw.json` : LLM router + Discord multi-channels
- 6 skills de base rédigés : `dev-reviewer`, `dev-architect`, `commercial-devis`, `admin-facturation`, `comm-linkedin`, `strategie-conseiller`
- `config/openclaw/HEARTBEAT.md` configuré
- `CLAUDE.md` rédigé
- `README.md` rédigé

---

## Template d'entrée

```
## YYYY-MM-DD

### [Composant] — [fichier modifié]
- Description de la modification
- Raison du changement (si non évidente)
```
