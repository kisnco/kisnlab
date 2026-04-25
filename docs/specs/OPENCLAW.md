# OPENCLAW.md — Agent IA, config, routing LLM, heartbeat

_Source de vérité pour la configuration OpenClaw._

---

## Rôle

OpenClaw est l'**agent IA conversationnel** central de KisnLab.
Il reçoit les messages Discord, route vers le bon skill, appelle le bon LLM, et maintient une mémoire long terme.

---

## Fichier de config

`config/openclaw/openclaw.json`

> Ne jamais modifier sans montrer le diff d'abord (règle CLAUDE.md).

---

## LLM Router

### Modèles

| Alias | Modèle | Usage | Max tokens |
|-------|--------|-------|-----------|
| `primary` | `claude-sonnet-4-20250514` | Tâches critiques | 4096 |
| `fast` | `claude-haiku-4-5-20251001` | Tâches simples | 2048 |

### Règles de routing

```
Skills critiques          → primary (Sonnet)
  dev-architect, dev-reviewer, strategie-conseiller,
  admin-juridique, admin-fiscalite, commercial-devis

Channels #dev, #strategie → primary (Sonnet)

Tout le reste             → fast (Haiku)
```

Objectif cible : **80% Haiku / 20% Sonnet** pour maîtriser les coûts.

---

## Mémoire

### Mémoire markdown (long terme par projet)

- Path : `/workspace/memory/` (monté depuis `config/openclaw/memory/`)
- Format : fichiers `.md` organisés par projet
- Non versionné (dans `.gitignore`)

### Mémoire vectorielle (sémantique)

- Provider : Postgres pgvector
- Table : `memory_embeddings` (base `openclaw`)
- Embedding model : Claude

---

## Heartbeat

Fichier : `config/openclaw/HEARTBEAT.md`

OpenClaw consulte ce fichier toutes les **30 minutes**.
Il poste dans `#alertes` **uniquement si une action est nécessaire** — silence sinon.

### Checks configurés

| Fréquence | Check |
|-----------|-------|
| Quotidien | Messages Discord sans réponse depuis +4h |
| Quotidien | Workflow n8n échoué dans les 24 dernières heures |
| Lundi 9h | Brief hebdomadaire des 5 projets → `#briefs` |
| Lundi 9h | Décisions stratégiques en attente → `#strategie` |
| Vendredi | Factures non payées depuis +7j → `#admin` |
| Vendredi | Résumé coûts Claude (Langfuse) → `#logs` |
| Immédiat | Erreur critique dans les logs → `#alertes` |
| Immédiat | Coût Claude > 5€ sur une tâche → `#alertes` |
| Immédiat | Tentative d'accès non autorisé → `#alertes` |

---

## Observabilité

Toutes les traces sont envoyées à **Langfuse** :
- Host : `http://langfuse:3000` (interne Docker)
- Clés : `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` (à remplir après 1er login Langfuse)

---

## Gateway

- Port interne : `18789`
- Exposé via Traefik → `http://openclaw.kisnlab.local`

---

## Outils autorisés / refusés

```yaml
allow: bash, read, write, edit, sessions_list, sessions_history
deny:  browser, gateway, cron
```

### Actions avec approbation obligatoire

`email_send` · `file_delete` · `git_push` · `payment` · `publish`

---

## Modèle de sécurité Docker + GitOps

> Voir aussi : `Dockerfile.openclaw`, `docker-compose.yml` services `openclaw` et `openclaw-dind`.

### Pourquoi cette architecture

OpenClaw est piloté par Discord — n'importe quel membre de la guild peut envoyer des messages. Un LLM **n'est pas une frontière de sécurité** : un payload de prompt injection peut le convaincre d'exécuter des commandes hostiles. Les accès qu'on lui donne doivent donc être limités au **strict nécessaire**, en partant du principe que le LLM peut être trompé.

### Image OpenClaw

- **Source** : `ghcr.io/openclaw/openclaw` (registry GitHub officiel du projet, pas le mirror Docker Hub)
- **Pinning** : par digest `sha256:...` dans `Dockerfile.openclaw` — pas de tag muable
- **Layer custom** : ajoute uniquement `docker-ce-cli` (dépôt Docker officiel signé) et `gh` CLI (dépôt GitHub officiel signé)
- **Mises à jour** : pour bumper, `docker pull ghcr.io/openclaw/openclaw:<version>` puis update du digest dans `Dockerfile.openclaw` + commit

### Accès Docker — DinD isolé

OpenClaw **ne parle pas** au daemon Docker du host. Il parle à un daemon dédié dans le container `openclaw-dind` (image `docker:26-dind`, privileged mais isolé) via TCP+TLS sur `tcp://openclaw-dind:2376`.

| Risque | Avant | Après |
|--------|-------|-------|
| Escape vers le host | `docker run -v /:/host privileged` → root sur le Mac | Confiné à la DinD |
| Modif du `docker-compose.yml` | Possible (repo en RW) | Impossible (repo en RO + branch protection) |
| Lecture des secrets `.env` | Possible | Impossible (`.env` non monté dans openclaw) |

Limites : la DinD reste `privileged: true`, donc une CVE du runtime Docker pourrait théoriquement permettre une escape. Risque résiduel surveillé via veille CVE.

### Accès au repo — Read-only + workflow GitOps

- `/repo/kisnlab` est monté **en lecture seule** dans OpenClaw (référence)
- Toute modification de code passe par :
  1. `gh repo clone kisnco/<repo> /workspace/work/<repo>`
  2. `git checkout -b feature/openclaw-<slug>`
  3. Commit + push sur la branche
  4. `gh pr create --draft --base dev --label openclaw-generated`
  5. **Review humaine obligatoire** via CODEOWNERS + branch protection
- `main` et `dev` sont protégées : pas de push direct, PR + 1 review minimum, status checks (`pr-checks`, `lint`, `healthcheck`) verts requis

### Hardening du container `openclaw`

Configuré dans `docker-compose.yml` :

- `cap_drop: [ALL]` — aucune capability Linux
- `security_opt: [no-new-privileges:true]` — pas d'escalation setuid
- `pids_limit: 512`, `mem_limit: 2g`, `cpus: "2.0"` — anti fork-bomb / DoS
- Réseau dédié `openclaw-dind-net` pour le canal DinD, séparé de `kisnlab-net`

À durcir dans une itération suivante : `read_only: true` + tmpfs (exige discovery des chemins d'écriture runtime).

### Token GitHub

`GITHUB_TOKEN` doit être un **fine-grained PAT** scopé sur `kisnco`, avec :
- Contents (RW), Pull requests (RW), Issues (RW), Workflows (**RO**)
- **Pas** de Secrets, Actions secrets, Administration
- Expiration 90 jours, rotation périodique

OpenClaw lit le token via `GH_TOKEN` (gh CLI le lit nativement, pas besoin de `gh auth login`).

### Workflow d'incident

Si un comportement suspect est détecté (alerte Langfuse, coût anormal, action inattendue) :

1. `docker compose stop openclaw` — couper l'agent
2. Examiner les traces Langfuse de la session
3. Si compromission confirmée :
   - `docker compose down openclaw openclaw-dind`
   - Révoquer `GITHUB_TOKEN` sur GitHub
   - Rotater `ANTHROPIC_API_KEY`, `DISCORD_BOT_TOKEN`, `OPENCLAW_WEBHOOK_SECRET`
   - `docker volume rm openclaw-dind-data openclaw-workspace` (purge le sandbox)
   - Audit du repo : `gh pr list --label openclaw-generated --state all`

---

## Projets trackés

| ID | Label | Type |
|----|-------|------|
| `scoreboard` | Scoreboard Python | Client |
| `site` | Site KIS'n Code | Perso |
| `app-mobile` | App Kis'n Way (Alignement) | Perso |
| `prestation` | Nouvelle prestation IA | Perso |
| `comptabilite` | Outil compta SASU | Perso |

---

## Setup Langfuse (étape 2 après 1er lancement)

1. Ouvrir `http://langfuse.kisnlab.local`
2. Créer un compte admin
3. Créer un projet **"KisnLab"**
4. Paramètres → API Keys → générer une paire
5. Ajouter dans `.env` : `LANGFUSE_PUBLIC_KEY` et `LANGFUSE_SECRET_KEY`
6. `docker compose restart openclaw`
