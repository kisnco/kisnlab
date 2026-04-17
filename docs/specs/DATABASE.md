# DATABASE.md — Schéma Postgres, tables, pgvector

_Source de vérité pour la base de données KisnLab._

---

## Infrastructure

- **Image** : `pgvector/pgvector:pg16`
- **Container** : `kisnlab-postgres`
- **Accès** : interne uniquement (pas de port exposé sur l'hôte)
- **Extension** : `pgvector` activée sur toutes les bases

---

## Bases de données

| Base | Propriétaire | Usage |
|------|-------------|-------|
| `openclaw` | `POSTGRES_USER` | Mémoire vectorielle, données agents |
| `n8n` | `POSTGRES_USER` | Workflows, credentials, executions n8n |
| `langfuse` | `POSTGRES_USER` | Traces LLM, métriques, coûts |

La base `kisnlab_main` est la base par défaut Postgres (variable `POSTGRES_DB`), non utilisée par les services.

---

## Base `openclaw` — Tables

### `memory_embeddings` — Mémoire vectorielle

_Gérée par OpenClaw automatiquement._

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | `uuid` | Identifiant unique |
| `project_id` | `text` | ID du projet (`scoreboard`, `site`...) |
| `content` | `text` | Contenu textuel du souvenir |
| `embedding` | `vector(1536)` | Vecteur d'embedding Claude |
| `metadata` | `jsonb` | Contexte additionnel (channel, skill, date...) |
| `created_at` | `timestamptz` | Date de création |

> Table créée par OpenClaw au 1er démarrage — ne pas créer manuellement.

---

## Base `n8n` — Tables

Gérées entièrement par n8n. Ne pas modifier manuellement.

Tables principales créées par n8n :
- `workflow_entity` — définitions des workflows
- `execution_entity` — historique des exécutions
- `credentials_entity` — credentials chiffrés (clé : `N8N_ENCRYPTION_KEY`)
- `webhook_entity` — webhooks actifs

---

## Base `langfuse` — Tables

Gérées entièrement par Langfuse via ses migrations automatiques. Ne pas modifier manuellement.

---

## Connexion depuis l'hôte (debug)

```bash
docker exec -it kisnlab-postgres psql -U kisnlab_admin -d openclaw
```

Commandes utiles :
```sql
-- Lister les tables
\dt

-- Voir les bases
\l

-- Vérifier pgvector
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Stats mémoire OpenClaw
SELECT project_id, COUNT(*) FROM memory_embeddings GROUP BY project_id;
```

---

## Backups (à mettre en place — V2 juin 2026)

- Outil : **Restic**
- Destination : **Backblaze B2**
- Fréquence : quotidien + avant chaque mise à jour majeure
- Rétention : 30 jours

En attendant, backup manuel avant toute opération risquée :
```bash
docker exec kisnlab-postgres pg_dumpall -U kisnlab_admin > backup_$(date +%Y%m%d).sql
```
