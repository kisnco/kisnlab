# FASTAPI.md — API centrale KisnLab

_Source de vérité pour le service `kisnlab-api`._

---

## Rôle

Service Python qui sert de pont entre OpenClaw (Discord) et LangGraph (orchestration multi-agents).
Accessible via Traefik sur `http://api.kisnlab.local`.

> Phase A : plomberie minimale, expose uniquement `/health`. Les agents LangGraph arrivent en Phase B.

---

## Structure

```
services/api/
├── Dockerfile              # python:3.12-slim + uvicorn
├── requirements.txt        # fastapi, uvicorn, pytest, httpx
├── pyproject.toml          # config pytest
├── .dockerignore
├── app/
│   ├── __init__.py
│   └── main.py             # FastAPI app + /health
└── tests/
    ├── __init__.py
    └── test_health.py
```

---

## Routes (V1)

| Méthode | Path | Réponse | Phase |
|---------|------|---------|-------|
| `GET` | `/health` | `{"status": "ok"}` | A |
| `POST` | `/agents/dev/run` | exécution agent dev (LangGraph) | B |
| `GET` | `/agents/executions` | historique en mémoire (50 derniers) | C |

---

## Variables d'environnement

| Variable | Usage | Phase |
|----------|-------|-------|
| `ANTHROPIC_API_KEY` | Clé Claude pour agents LangGraph | A (préparée) / B (utilisée) |
| `KISNLAB_API_TOKEN` | Bearer token pour authentifier OpenClaw → API | A |
| `LOG_LEVEL` | Niveau de log uvicorn | A |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | Tracing | C |

---

## Réseau Docker

- Réseau : `kisnlab-net` uniquement (pas de DinD)
- Container : `kisnlab-api` (préfixe convention CLAUDE.md)
- Port interne : `8000`
- Exposé via Traefik → `http://api.kisnlab.local`

URLs internes inter-services : `http://kisnlab-api:8000` (alias container, convention DNS adoptée 2026-04-26).

---

## Commandes

```bash
# Démarrer le service
docker compose up -d kisnlab-api

# Logs
docker compose logs -f kisnlab-api

# Tests dans le container
docker compose exec kisnlab-api python -m pytest

# Tests en local (sans Docker)
cd services/api && pip install -r requirements.txt && python -m pytest

# Healthcheck depuis le host
curl http://api.kisnlab.local/health
```

---

## Décisions architecturales

- **pip + requirements.txt** plutôt que poetry/uv : simplicité, alignement KIS, image légère
- **Pas de DB en V1** : historique d'exécutions en mémoire (liste circulaire 50 derniers). Postgres ajouté plus tard si besoin.
- **Pas de cockpit web** : Langfuse couvre déjà l'observabilité. Pilotage via Discord (OpenClaw → API).
- **1 seul agent en V1** (`dev`) : valider la plomberie LangGraph avant d'ajouter `commercial`/`admin`/`comm`.

---

## Roadmap

- [x] Phase A — Plomberie FastAPI + `/health`
- [ ] Phase B — Premier agent LangGraph (`dev`, modèle Haiku)
- [ ] Phase C — Tracing Langfuse + historique en mémoire
- [ ] Phase D — Skill OpenClaw `delegate-to-api`
- [ ] Phase F (later) — Agents `commercial`, `admin`, `comm` + supervisor
