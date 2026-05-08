# CHANGELOG.md — Historique des modifications

_Toute modification significative de la stack, des configs ou des specs doit être loguée ici._

Format : `[YYYY-MM-DD] [composant] description`

---

## 2026-05-08

### Migration agentique — Phase D : skill OpenClaw `delegate-to-api` + auth Bearer

OpenClaw peut désormais déléguer une tâche à l'agent `dev` de `kisnlab-api` depuis Discord. Phase D câble aussi l'auth Bearer côté API qui était préparée mais non activée en Phase A.

- **`skills/delegate-to-api/SKILL.md`** : nouveau skill (channel `#dev`, LLM Haiku, pas d'`approval` — appel inter-service interne au stack). Trigger sur "délègue dev :", "agent dev :", "demande à dev de". Curl POST vers `http://kisnlab-api:8000/agents/dev/run` avec Bearer, body construit via `jq -nc --arg` (JSON-safe), timeout 60s, restitution brute de la réponse dans le channel.
- **Auth Bearer côté FastAPI** : `services/api/app/auth.py` (dependency `verify_token`), router `/agents/*` protégé via `dependencies=[Depends(verify_token)]`. `/health` reste public. Codes : 200 OK, 401 token manquant/invalide, 503 si `KISNLAB_API_TOKEN` non configuré côté serveur.
- **`docker-compose.yml`** : ajout `KISNLAB_API_TOKEN: ${KISNLAB_API_TOKEN}` dans `services.openclaw.environment` (seul service existant touché — modif minimale d'une ligne d'env).
- **Tests** : 5 nouveaux tests d'auth (sans token, mauvais token, token valide, `/health` public, 503 si token serveur absent). `services/api/tests/conftest.py` : fixture autouse `disable_auth` (override par défaut pour les tests existants) + fixture `enable_auth` (opt-in pour les tests d'auth).
- **Specs** : `OPENCLAW.md` (nouvelle section "Délégation à FastAPI / LangGraph"), `SKILLS.md` (ligne `delegate-to-api`), `FASTAPI.md` (section "Authentification").

OpenClaw reste l'agent IA conversationnel principal sur Discord — la délégation est une capacité ajoutée, pas un remplacement de ses skills existants. Les agents `commercial`/`admin`/`comm`/`supervisor` arriveront en Phase F.

### Migration agentique — Phase B : premier agent LangGraph (`dev`)

Premier graphe LangGraph hébergé dans `kisnlab-api`. Endpoint `POST /agents/dev/run` qui appelle Claude Haiku via un graphe à 1 node.

- **`services/api/app/agents/dev.py`** : graphe LangGraph (StateGraph) avec un seul node `call_claude`. État `DevState{task, response}`. Modèle `claude-haiku-4-5-20251001`. System prompt positionne l'agent en bras technique KIS'n Code (français, code anglais, KIS, concis).
- **`services/api/app/routers/agents.py`** : router FastAPI avec `POST /agents/dev/run` (body `RunRequest{task}`, réponse `RunResponse{agent, response}`). Validation Pydantic (task non vide, ≤ 8000 chars).
- **`services/api/app/main.py`** : `include_router(agents.router)`, version bumpée 0.1.0 → 0.2.0.
- **`services/api/requirements.txt`** : ajout `langgraph==0.2.60` et `langchain-anthropic==0.3.1`.
- **`services/api/tests/test_dev_agent.py`** : 4 tests — unit (mock ChatAnthropic), endpoint mocké, validation 422, intégration réelle (skipif sans `ANTHROPIC_API_KEY` ou clé placeholder).
- **Spec créée** : `docs/specs/LANGGRAPH.md` (rôle, pattern routing, agents disponibles, graphe `dev` V1, règle validation envois externes, dépendances, roadmap).
- **Mise à jour** : `FASTAPI.md` (structure étendue + détails route `POST /agents/dev/run` + roadmap).

**Décisions** :
- 1 node (KIS) plutôt que 2 (`intent → claude`) — extensible plus tard quand des tools arrivent (lecture repo, run tests, gh CLI).
- Pas de DB, pas de tracing en Phase B (Phase C s'en occupe).
- Modèle Haiku confirmé par défaut V1, bascule Sonnet agent par agent quand prompts stables.

### Migration agentique — Phase A : plomberie FastAPI

Démarrage de la migration multi-agents (FastAPI + LangGraph). Phase A livre la **plomberie minimale** : un service Python qui répond `/health` derrière Traefik. Les agents LangGraph arrivent en Phase B.

- **Nouveau service** : `kisnlab-api` (image `python:3.12-slim` build local depuis `services/api/`). Réseau `kisnlab-net` uniquement (pas de DinD, pas de Postgres). Exposé via Traefik sur `http://api.kisnlab.local`.
- **`services/api/`** : `Dockerfile` (uvicorn), `requirements.txt` (fastapi, uvicorn, pydantic, pytest, httpx), `app/main.py` (un seul endpoint `GET /health` → `{"status":"ok"}`), test pytest `tests/test_health.py`.
- **`docker-compose.yml`** : ajout du service `kisnlab-api` entre `rsshub` et `clickhouse`.
- **`.env.example`** : ajout `KISNLAB_API_TOKEN` (Bearer pour auth OpenClaw → API, à générer via `openssl rand -hex 32`).
- **`/etc/hosts`** : ajout `127.0.0.1 api.kisnlab.local`.
- **Spec créée** : `docs/specs/FASTAPI.md` (rôle, structure, routes V1, env, commandes, roadmap).
- **Mises à jour** : `CLAUDE.md` § Stack active, `STACK.md` § Services + /etc/hosts.

**Décisions** :
- pip + `requirements.txt` plutôt que poetry/uv (KIS, image légère, alignement avec le reste du projet).
- Pas de cockpit web (Langfuse couvre déjà l'observabilité).
- Pas de DB en V1 (historique en mémoire, ajouté plus tard si besoin).
- 1 seul agent (`dev`) en V1 — `commercial`/`admin`/`comm` reportés en Phase F.
- Branche dédiée `feat/fastapi-langgraph` depuis `dev`.

**Phase 2 Langfuse OTel toujours bloquée** — la Phase A n'en dépend pas, le tracing sera branché en Phase C avec encaissement silencieux du SDK si Langfuse n'est pas opérationnel.

---

## 2026-04-26

### Pipeline veille — RSSHub + workflow n8n `strategie-publier-veille`

Câblage du pipeline Veille en mode passif (n8n fetche, OpenClaw synthétise).

- **`docker-compose.yml`** : nouveau service `rsshub` (`diygod/rsshub:latest`, interne kisnlab-net, cache Redis DB 2, healthcheck `/healthz`). Pas de Traefik, pas de port host, aucune nouvelle var `.env`.
- **`docker-compose.yml`** : section `n8n.environment` reçoit `OPENCLAW_WEBHOOK_SECRET` et `OPENCLAW_WEBHOOK_URL=http://kisnlab-openclaw:18789/plugins/webhooks/n8n` (utilisée via `{{$env.OPENCLAW_WEBHOOK_*}}` dans le workflow, secret jamais sérialisé en JSON).
- **`workflows/strategie-publier-veille.json`** : 3 nodes — Schedule Trigger (`30 9 * * *` Europe/Paris) → Code "Fetch + Filter + Build payload" (33 sources : 5 IA, 6 Dev, 3 Business-FR, 3 Sécu, 15 X via RSSHub ; parser RSS/Atom maison, `Promise.all` + timeout 10s, fenêtre 24h glissantes, dédupe URL, top 60 items) → HTTP Request POST OpenClaw webhook avec `action: create_flow` et `goal` contenant les items pré-fetchés.
- **Test webhook validé** : `wget` depuis n8n vers `kisnlab-openclaw:18789/plugins/webhooks/n8n` avec Bearer renvoie `{"ok":true,...}`. Workflow importé manuellement dans n8n UI puis activé après run de test.
- **X via RSSHub** : option A retenue — sans cookie auth, RSSHub renvoie 503 sur `/twitter/user/<handle>`. Le workflow encaisse silencieusement (`fetchSource` retourne `[]`), le skill `strategie-veille` écrit "RAS aujourd'hui" pour la section X. À évaluer après 1-2 semaines : passer à l'option B (cookie `auth_token` injecté) si X est trop muet.

**Bug DNS Docker corrigé en passant** : le service name `openclaw` ne résout pas depuis n8n alors que `kisnlab-openclaw` (nom de container) le fait. Convention adoptée pour toutes les URLs internes inter-services. `docs/specs/N8N.md` corrigé en conséquence.

### Skill — `strategie-veille` créé

Skill OpenClaw P2 du backlog `SKILLS.md` livré. Veille quotidienne sur 4 axes (IA & agentique en focus, dev/IT, business/FR pour entrepreneurs IT, sécurité). Mode actif (l'agent fetche lui-même via le plugin browser), digest narratif court, ton Kael (cynique sec, factuel d'abord). Triggers : `veille`, `veille IA`, `veille dev`, `veille business`, `veille sécu`, `quoi de neuf en [sujet]` dans `#strategie`.

Sources V1 : Anthropic News, OpenAI News, Hugging Face, The Batch, Latent Space, HN, DEV.to, GitHub Trending, Maddyness, Frenchweb, BFM Tech, The Hacker News, Krebs, ANSSI, Snyk. **Source X/Twitter reportée V2** (token API X non configuré).

Pas encore de workflow n8n CRON matin associé — création conditionnelle après validation manuelle du skill seul (cf. feedback_external_actions).

### CI — Job gate par workflow GitHub Actions

`scripts/setup-branch-protection.sh` attendait des contextes de status checks `pr-checks`, `lint`, `healthcheck` qui n'existaient pas — les 3 workflows définissaient plusieurs jobs aux noms différents. Activer la branch protection en l'état aurait bloqué toutes les PR éternellement.

**Fix** : chaque workflow expose maintenant un job final `pr-checks` / `lint` / `healthcheck` qui dépend de tous ses sous-jobs (`if: always()` + agrégation via `contains(needs.*.result, 'failure')`). La branch protection cible un seul check par workflow.

Bonus : `lint.yml` migré de `docker-compose` (V1 hyphenated, plus dispo sur ubuntu-latest) vers `docker compose` (V2 plugin).

### CI — Branch protection activée sur `main` et `dev`

Via `scripts/setup-branch-protection.sh` : 1 review requise (CODEOWNERS), status checks `pr-checks`/`lint`/`healthcheck` obligatoires, force push interdit, deletions interdites, conversation resolution requise. `enforce_admins=false` (Mélodie peut bypass via UI ; OpenClaw, sans droits admin, doit passer par PR).

### Cleanup — Workflow n8n cassé + projet Langfuse doublon

- **n8n** : `admin-relancer-factures` importé via CLI s'était retrouvé avec un id vide en DB (bug n8n CLI). Cleanup SQL : `DELETE FROM shared_workflow WHERE "workflowId"=''; DELETE FROM workflow_entity WHERE id=''` — 2 rows. Reste 2 workflows valides (`dev-generer-brief-hebdo`, `openclaw-langfuse-tracker`).
- **Langfuse** : org `kisnlab` + projet `kisnlab-main` créés par les `LANGFUSE_INIT_*` du compose étaient en doublon (vides) de l'org `KIS'n Code` + projet `KIS'n Lab` créés manuellement via l'UI. Org `kisnlab` supprimée (CASCADE → projet `kisnlab-main` + ses tables enfants). Variables `LANGFUSE_INIT_*` retirées du `docker-compose.yml` pour ne pas recréer le doublon au prochain start.

### Fix — Réseau OpenClaw perdu au `--force-recreate`

Lors du fix exec wedge (rebuild OpenClaw), le `docker compose up -d --force-recreate openclaw` n'avait rattaché que `openclaw-dind-net`, perdant `kisnlab-net`. Conséquence : OpenClaw ne pouvait plus joindre Langfuse, Postgres, Redis... pour traces et webhooks. Réparé via `docker network connect kisnlab-net kisnlab-openclaw`. Le compose déclare bien les 2 réseaux ; un `docker compose up -d` (sans force-recreate) suffit pour réattacher correctement.

### Observabilité — Config OTel OpenClaw → Langfuse v3 (en cours)

`diagnostics.otel.*` paramétré dans `openclaw.json` : endpoint `http://langfuse-web:3000/api/public/otel`, protocol `http/protobuf`, header `Authorization: Basic <base64(public:secret)>`, serviceName `openclaw`, traces `true`, sampleRate `1`. Endpoint Langfuse OTLP testé avec auth manuel : `HTTP 200`. Gateway redémarré.

**Bloqueur** : aucune trace n'arrive dans `traces`/`observations` ClickHouse après un agent run de test. Aucun log d'init OTel/exporter dans les logs OpenClaw au boot. Hypothèse : la section `diagnostics.otel.*` est déclarative dans le schema mais non câblée côté runtime, ou nécessite des env vars OTEL_* standard. À investiguer dans une prochaine session.

## 2026-04-25

### Fix — OpenClaw exec wedge : `/home/node/.openclaw/` root-owned

**Symptôme** : tous les `exec` et `edit` de l'agent échouaient en `EACCES: permission denied, open '/home/node/.openclaw/.exec-approvals.*.tmp'`. Le système d'approval ne pouvait pas écrire son fichier temporaire → tout le tooling wedgé.

**Cause** : Docker créait `/home/node/.openclaw/` à la volée en `root:root` lors de la résolution du bind-mount `./volumes/openclaw-agent-workspace:/home/node/.openclaw/workspace`. L'agent (uid 1000) ne pouvait écrire que dans le sous-dossier `workspace/` mounté, pas à la racine. Le `chown` runtime est bloqué par `cap_drop: ALL` + `no-new-privileges`, donc le fix devait passer par l'image.

**Fix** : `Dockerfile.openclaw` pré-crée `/home/node/.openclaw/` avec `install -d -o node -g node -m 0755` avant le `USER node`. Au prochain start, le bind-mount enfant se pose sur un parent déjà writable.

### Sécurité — Isolation Docker OpenClaw + workflow GitOps PR

Pattern 1 (Docker-in-Docker isolé) + Pattern 3 (modifications via PR draft) — voir `docs/specs/OPENCLAW.md` § "Modèle de sécurité Docker + GitOps" et `/Users/melo/.claude/plans/floofy-tickling-sky.md`.

**Avant** : OpenClaw montait `/var/run/docker.sock` du Mac et le repo en RW → un payload de prompt injection Discord pouvait escape vers le host (équivalent root).

**Après** :
- Nouveau service `openclaw-dind` (image `docker:26-dind`, privileged mais isolé) — OpenClaw parle à ce daemon via TCP+TLS, pas au socket du host
- `/repo/kisnlab` monté en **lecture seule** ; nouvelle volume `openclaw-workspace` pour les écritures jetables
- Modifications de code via `gh repo clone` → branche `feature/openclaw-*` → PR draft sur `dev` (label `openclaw-generated`)
- Branch protection sur `main` + `dev` (PR obligatoire, 1 review CODEOWNERS, status checks verts)
- Hardening container : `cap_drop: [ALL]`, `no-new-privileges: true`, `pids_limit: 512`, `mem_limit: 2g`, `cpus: "2.0"`
- Nouveau réseau dédié `openclaw-dind-net` (isolé de `kisnlab-net`)

### Image — Build maison `kisnlab/openclaw:custom`

- Création de `Dockerfile.openclaw` : `FROM ghcr.io/openclaw/openclaw@sha256:9d5f1...` (source officielle, pas le mirror Docker Hub) + ajout de `docker-ce-cli` et `gh` CLI depuis leurs dépôts apt signés
- `docker-compose.yml` service `openclaw` : `image:` remplacé par `build:` pointant vers `Dockerfile.openclaw`

### Skill — `dev-project-manager` réécrit

- Retrait des appels `curl --unix-socket` (plus d'accès au socket host)
- Ajout du flow GitOps : clone via gh → branche → commit → push → `gh pr create --draft`
- Suppression de la commande Discord `"redémarre [service]"` (non utilisée)
- Reformulation `"état de la stack"` → `"état des projets"` (lecture GitHub via gh CLI)
- Ajout d'une section "Ce que tu ne peux PAS faire (par design)"

### GitHub — Templates et branch protection

- Création `.github/CODEOWNERS` (placeholder à remplir avec ton GitHub username)
- Création `.github/PULL_REQUEST_TEMPLATE.md` (sections Quoi/Pourquoi/Tests/Sécurité)
- Création `scripts/setup-branch-protection.sh` (à exécuter manuellement après `gh auth login`)

### Configuration

- `.env.example` : ajout de `GITHUB_TOKEN` (oversight précédent — la variable était consommée sans être documentée), avec recommandation fine-grained PAT
- `scripts/preflight.sh` : nouveaux checks (Dockerfile.openclaw présent, socket Docker non monté dans openclaw, repo en RO, docker+gh CLI présents dans le container, GITHUB_TOKEN dans `.env`, dossiers volumes/ créés)

### Comportement OpenClaw — Bootstrap files persistants + directives

L'agent workspace `/home/node/.openclaw/workspace/` (qui contient `USER.md`, `SOUL.md`, `AGENTS.md` et autres fichiers bootstrap injectés dans le system prompt) était recréé vierge à chaque démarrage. Conséquence observée : OpenClaw répondait en anglais et demandait l'org/repo GitHub à chaque session, au lieu d'utiliser le `GH_TOKEN` déjà fourni.

Fix :
- Bind mount `./volumes/openclaw-agent-workspace:/home/node/.openclaw/workspace` (persistance)
- `USER.md` rempli : profil de Mélodie, directive "réponds toujours en français", projet par défaut `kisnco/kisnlab`, instructions "essaie `gh auth status` + `gh repo list kisnco` avant de demander"
- Skill `dev-project-manager` : ajout d'un en-tête "Règles non-négociables" pour belt-and-suspenders côté skill loading

### Volumes — Migration vers bind mounts dans `./volumes/`

Tous les volumes Docker (postgres, redis, n8n, clickhouse, openclaw, openclaw-workspace, openclaw-dind-*) basculés depuis des **named volumes Docker-managed** vers des **bind mounts** dans `./volumes/<name>/`.

**Bénéfices** :
- Inspection directe depuis macOS (pratique pour debug, backup)
- Tout est dans le projet — facile à archiver, déplacer

**Trade-offs assumés** :
- Performance Postgres ~30% plus lente sur virtiofs vs named volume (acceptable en dev)
- DinD `/var/lib/docker` sur bind mount macOS = risque overlay2 selon version Docker Desktop ; fallback documenté dans `docker-compose.yml` et `STACK.md` (repasser en named volume si besoin)

**Migration des données** : les 500+ MB existants (postgres 94 MB, clickhouse 385 MB, etc.) ont été copiés depuis les named volumes Docker vers `./volumes/` avant la bascule. Aucune perte de donnée.

- `docker-compose.yml` : services postgres, redis, n8n, clickhouse, openclaw, openclaw-dind reconfigurés en bind mounts ; section `volumes:` globale supprimée
- `.gitignore` : ajout de `volumes/`
- `docs/specs/STACK.md` § "Volumes persistants" : tableau réécrit

### Hors scope (à traiter dans des itérations dédiées)

- Rotation de la clé Anthropic en clair dans `config/openclaw/agents/main/auth-profiles.json`
- Restriction du tool profile (`"coding"` → allowlist)
- `read_only: true` + `user:` override sur openclaw (exige discovery des chemins runtime)
- Egress proxy avec allowlist domaines
- Hardening du system prompt contre prompt injection

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
