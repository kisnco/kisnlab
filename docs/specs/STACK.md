# STACK.md — Services Docker

_Source de vérité pour l'infrastructure KisnLab._

---

## Vue d'ensemble

Stack IA auto-hébergée tournant sur **MacBook Pro Intel 2019 (32 Go)** en local.
Accès via domaines `.kisnlab.local` routés par Traefik.

---

## Services

| Service | Image | Rôle | URL locale |
|---------|-------|------|-----------|
| **Traefik** | `traefik:v3.2` | Reverse proxy, routing par domaine | `http://traefik.kisnlab.local` |
| **Postgres** | `pgvector/pgvector:pg16` | Base relationnelle + vectorielle | interne uniquement |
| **Redis** | `redis:7-alpine` | Queue et cache pour n8n | interne uniquement |
| **OpenClaw** | `kisnlab/openclaw:custom` (build local — voir `Dockerfile.openclaw`) | Agent IA conversationnel Discord | `http://openclaw.kisnlab.local` |
| **OpenClaw-DinD** | `docker:26-dind` | Daemon Docker isolé (sandbox d'exécution OpenClaw) | interne uniquement |
| **n8n** | `n8nio/n8n:latest` | Workflows automatisés | `http://n8n.kisnlab.local` |
| **Langfuse** | `langfuse/langfuse:latest` | Observabilité LLM | `http://langfuse.kisnlab.local` |

---

## Ports exposés sur l'hôte

| Port | Service | Usage |
|------|---------|-------|
| `80` | Traefik | Entrée HTTP pour tous les services |

> Postgres (5432) et Redis (6379) ne sont **pas** exposés sur l'hôte — internes uniquement.
> Le dashboard Traefik est accessible via `http://traefik.kisnlab.local` avec basicauth.

---

## Réseau Docker

```
kisnlab-net (bridge)
└── tous les services métier (postgres, redis, openclaw, n8n, langfuse, ...)

openclaw-dind-net (bridge, isolé)
└── openclaw ↔ openclaw-dind uniquement
    objectif : éviter qu'une compromission de la DinD parle à postgres/redis
```

OpenClaw est dual-homed sur les deux réseaux : `kisnlab-net` (pour postgres/redis/langfuse) et `openclaw-dind-net` (pour parler à la DinD via TCP+TLS).

---

## Volumes persistants

Tous les volumes sont des **bind mounts** vers `./volumes/<name>/` (gitignored). Permet l'inspection directe depuis macOS et facilite le backup.

| Chemin host | Service | Contenu |
|-------------|---------|---------|
| `./volumes/postgres` | Postgres | Données BDD (3 databases : openclaw, n8n, langfuse) |
| `./volumes/redis` | Redis | Queue persistante n8n |
| `./volumes/openclaw` | OpenClaw | Cache et données internes (`/data`) |
| `./volumes/n8n` | n8n | Credentials, workflows, executions |
| `./volumes/clickhouse` | ClickHouse | Données Langfuse (analytics) |
| `./volumes/openclaw-dind-certs-ca` | OpenClaw-DinD | Certs TLS CA auto-générés par dind |
| `./volumes/openclaw-dind-certs-client` | OpenClaw-DinD ↔ OpenClaw | Certs TLS client (RO côté openclaw) |
| `./volumes/openclaw-dind-data` | OpenClaw-DinD | Storage du daemon (images, builds, containers du sandbox) — **à purger périodiquement** : `docker exec kisnlab-openclaw-dind docker system prune -af` |
| `./volumes/openclaw-workspace` | OpenClaw | Workspace de travail jetable (clones git, builds) |

> ⚠️ **DinD sur macOS** : si `openclaw-dind` ne démarre pas (logs `overlay2: failed to mount`), `./volumes/openclaw-dind-data` est probablement incompatible avec overlay2 sur ta version de Docker Desktop. Solution : repasser ce volume en named volume Docker (cf. commentaire dans `docker-compose.yml`).

---

## Dépendances de démarrage

```
Postgres (healthy) ──────┬─→ OpenClaw
                         └─→ n8n
                         └─→ Langfuse

Redis (healthy) ─────────┬─→ OpenClaw
                         └─→ n8n

OpenClaw-DinD (healthy) ──→ OpenClaw   (TCP+TLS sur :2376, certs auto)
```

---

## /etc/hosts requis

```
127.0.0.1   openclaw.kisnlab.local
127.0.0.1   n8n.kisnlab.local
127.0.0.1   langfuse.kisnlab.local
127.0.0.1   traefik.kisnlab.local
```

---

## Variables d'environnement critiques

Toutes dans `.env` (jamais committées). Voir `.env.example` pour la liste complète.

| Variable | Usage |
|----------|-------|
| `ANTHROPIC_API_KEY` | Clé Claude API |
| `POSTGRES_USER / PASSWORD` | Auth Postgres |
| `REDIS_PASSWORD` | Auth Redis |
| `N8N_ENCRYPTION_KEY` | Ne jamais changer après 1er lancement |
| `LANGFUSE_SECRET / SALT` | Auth Langfuse |
| `TRAEFIK_DASHBOARD_AUTH` | Basicauth dashboard Traefik (htpasswd format) |
| `DISCORD_BOT_TOKEN` | Token bot Discord |

---

## Plan V2 — Juin 2026

Migration sur **Mac mini M4 Pro 48 Go** :
- KisnLab tourne 24/7 en production
- Ollama local (Llama 70B Q4) pour inférence gratuite
- HTTPS via Cloudflare Tunnel ou Let's Encrypt
- Backups Postgres avec Restic + Backblaze B2

> Le Scaleway PLAY2-MICRO est réservé à Kis'n Way et site KIS'n Code — ne pas y déployer KisnLab.