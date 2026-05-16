# CHANGELOG.md — Historique des modifications

_Toute modification significative de la stack, des configs ou des specs doit être loguée ici._

Format : `[YYYY-MM-DD] [composant] description`

---

## 2026-05-16

### Phase 2 — Mémoire conversationnelle des agents (LangGraph checkpointer)

Branche `feat/agent-memory-langgraph`. Fix du bug observé en test live : Dev oubliait tout entre deux tours d'une même conversation Discord.

- **`state.py`** : `TeamState` et `DevState` portent un champ `messages: Annotated[list[AnyMessage], add_messages]` (historique de conversation). `AgentRequest` accepte `thread_id: Optional[str]`.
- **`team.py`** : `build_team_graph(checkpointer=None)` — si fourni, le graphe persiste l'historique par `thread_id`. Le node `delegate` transmet `state.messages` au sous-graphe `dev` et enregistre la réponse via `add_messages`.
- **`dev.py`** : `call_claude` envoie tout l'historique à l'agent ReAct (fallback `HumanMessage(task)` si pas d'historique → one-shot `/agents/dev/run` inchangé).
- **`routers/agents.py`** : `team_graph` compilé avec `MemorySaver()` (in-memory). `/agents/team/run` mappe `thread_id` → `config.configurable.thread_id` ; absent → clé `ephemeral:<uuid>` (appel isolé, rétrocompatible).
- **`dev-bot/main.py`** : envoie `thread_id = f"discord:{channel_id}"` — un fil de mémoire par channel.
- **`dev_base.md`** : retrait du workaround « tu es stateless » de la Phase 1 — Dev sait désormais qu'il a une mémoire conversationnelle et tient compte de l'historique.

Périmètre : **Reviewer reste one-shot** (opère sur une référence de PR, pas un fil). Mémoire **in-memory** — vidée au redémarrage de `kisnlab-api` ; passage à `PostgresSaver` (persistant) prévu en PR ultérieure.

Tests : 90 verts (+11 — conversation 3 tours avec contexte cumulé, isolation entre threads, fallback stateless). Spec `LANGGRAPH.md` § Phase 2 mise à jour.

### Polissage post-test live dev team (mention split + format reviewer + comportement Dev stateless)

Première session de tests live Discord de l'équipe dev (Dev + Reviewer + Team). Trois bugs UX/archi observés et fixés sur la branche `feat/dev-team-discord-bot` :

- **Bug 1 — Kael répondait aux mentions `@Dev`** : config OpenClaw `requireMention: false` faisait répondre Kael à tout message du channel allowlisté. Passé à `true` via `docker exec kisnlab-openclaw openclaw config set channels.discord.guilds.<id>.requireMention true`. Kael ne répond plus que sur `@Kael`. (Note : `openclaw.json` est gitignored, changement à reproduire si stack reconstruite from scratch.)
- **Bug 2 — Reviewer produisait un mur de texte** : les 3 skills `security_review.md`/`quality_review.md`/`architecture_review.md` n'imposaient aucune contrainte de format. Ajout d'une section « Format de sortie (obligatoire) » : `findings` = liste markdown, max 3 puces ≤ 140 chars, pas de citation littérale du diff. Sortie review passe de ~80 lignes prose à ~15 lignes structurées (3 sections × ≤3 puces).
- **Bug 3 — Dev forçait le workflow PR sur questions générales** : sans référence PR explicite, Dev demandait quand même « quel repo ? » et proposait de lister les PRs. Ajout dans `dev_base.md` d'une section « Mode de fonctionnement » qui rend explicites les contraintes stateless (pas de mémoire entre messages, pas d'accès FS) et la matrice de réponse selon le type de demande (question conceptuelle / analyse PR / ambigu). Gating « quand utiliser ces outils » ajouté en tête de `github_pr_tools.md`.

Refactor lié (post-review du reviewer sur PR #10) :

- **`services/api/app/agents/observability.py`** : nouveau module — factorisation de `_build_langfuse_callbacks` (auparavant dupliqué dans `dev.py`/`reviewer.py`/`team.py`). Singleton `LANGFUSE_CALLBACKS` construit une seule fois à l'import.
- **`services/api/app/agents/state.py`** : nouvelle fonction `read_field(result, field)` — était dupliquée dans `team.py` et `routers/agents.py` (signalée par le reviewer comme abstraction transversale à centraliser).
- **`services/api/app/agents/team.py`** : propagation `metadata={"routed_to": ..., "routed_from": "team"}` dans le `config` des invocations sub-graph → visible sur les traces Langfuse `dev_agent` / `reviewer_<perspective>` (debug : filtrer les runs passés par le team router).
- **Tests `tests/test_skills_loader.py`** : assertions ajustées sur invariants stables (`KisnLab`, `gh_pr_diff`, `français`) après réécriture des skills.

Tests : 72 verts + 7 skipped (intégration). Mémoire conversationnelle (LangGraph `MemorySaver` + `thread_id = channel_id`) délibérément différée à la **Phase 2** — workaround actuel : skills explicites sur le mode stateless. Décision tracée dans la mémoire Claude (`project_phase2_agent_memory.md`).

### Architecture — Bot Discord dédié à la dev team (séparation Kael ↔ Dev Team)

Suite à la persistence du bug de skill matching (`delegate-to-api` capturait les commandes destinées à `delegate-to-reviewer`/`delegate-to-team` malgré le Fix 2 sur les triggers), refonte de l'entrée Discord pour la dev team. L'équipe dev a maintenant **sa propre identité Discord** (bot `KisnLab Dev Team`), distincte de Kael (OpenClaw).

- **Nouveau service `kisnlab-dev-bot`** (`services/dev-bot/`) : listener Python `discord.py` ~120 LOC. Écoute uniquement les mentions du bot Dev Team venant de l'utilisateur allowlisté, transmet chaque tâche à `POST /agents/team/run` (le superviseur LangGraph route ensuite vers `dev` ou `reviewer`). Réponse postée en thread reply Discord avec préfixe `[dev]` ou `[reviewer]`. Long output découpé en chunks Discord-friendly (2000 chars max, coupe préférée sur saut de ligne).
- **`services/dev-bot/Dockerfile`** : image Python 3.12-slim, déps minimales (`discord.py==2.4.0`, `httpx==0.27.2`).
- **`docker-compose.yml`** : nouveau service `kisnlab-dev-bot` (`depends_on: kisnlab-api`, pas de Traefik — pas d'endpoint HTTP exposé).
- **`.env.example`** : nouvelle var `DISCORD_DEV_BOT_TOKEN` documentée.
- **Suppression côté Kael** des 3 skills `delegate-to-api`, `delegate-to-reviewer`, `delegate-to-team` — Kael n'orchestre plus rien vers FastAPI. Séparation nette : Kael pour le généraliste (admin/comm/commercial/stratégie), Dev Team pour les tâches techniques.
- **Tests** : 11 verts pour les helpers du bot (`_strip_mention`, `_format_response` avec split intelligent sur saut de ligne, fallback hard cut). Tests `kisnlab-api` inchangés (72 verts + 7 skipped).
- **Docs** : `DISCORD.md` (2 bots, configuration séparée), `LANGGRAPH.md` (nouveau pattern de routing, agent dev correctement décrit comme read-only), `SKILLS.md` (suppression skills + nouvelle section "Pont Discord ↔ kisnlab-api"), `CLAUDE.md` (table stack étendue).

### Fix — Agent dev en lecture seule + triggers `delegate-to-api` resserrés

Suite à un test Discord où la commande `review la PR #10 de kisnco/kisnlab` a déclenché `delegate-to-api` (au lieu de `delegate-to-reviewer`) **et** où l'agent dev a posté une vraie review GitHub `REQUEST_CHANGES` sans validation manuelle — violation directe de la règle « actions externes ⇒ approval requis ».

- **`services/api/app/agents/tools/github_tools.py`** : `GITHUB_PR_TOOLS` réduit aux outils **lecture seule** (`gh_pr_list`, `gh_pr_get`, `gh_pr_diff`). `gh_pr_review` et `gh_pr_comment` sont déplacés dans `GITHUB_PR_WRITE_TOOLS` (défini mais non exposé à l'agent dev). L'agent dev ne peut plus écrire sur GitHub. Si une publication automatique est un jour souhaitée, elle passera par un skill dédié avec `approval: required`.
- **`services/api/app/agents/skills/github_pr_tools.md`** : prompt système ré-écrit. Plus aucune instruction « poste une review structurée » ; le skill explicite « Tu **ne postes jamais** sur GitHub : tu n'as pas d'outil d'écriture ».
- **`skills/delegate-to-api/SKILL.md`** : nouvelle section « Tu ne déclenches PAS sur » qui exclut explicitement les patterns gérés par `delegate-to-reviewer` et `delegate-to-team` (`/review`, `/team`, URL `github.com/.../pull/N`, raccourci `owner/repo#N`, narratif). Évite que `delegate-to-api` continue d'attraper les commandes destinées aux nouveaux skills.
- **Tests** : 72 verts + 7 skipped. Aucune régression — les tests `test_gh_pr_review` et `test_gh_pr_comment` continuent de tester les fonctions individuellement (toujours définies, juste retirées du tool list par défaut).
- **Note opérationnelle** : la review hallucinée postée sur PR #10 (déjà mergée) reste visible sur GitHub. Aucune action requise — la PR est mergée, le commentaire est inoffensif. Pas de rollback.

### Phase 1 — Pont Discord pour reviewer/team (PR-4/4) — CLÔTURE PHASE 1

Deux nouveaux skills OpenClaw exposent les agents `reviewer` et `team` côté Discord. **Aucune modification de code Python ou de tests**, uniquement skills + doc.

- **`skills/delegate-to-reviewer/SKILL.md`** : skill "passeur de plat" qui appelle `POST /agents/reviewer/run`. Triggers : `/review <PR>`, "review la PR …", "fais une review de …". Surface les `metadata.severities` (security/quality/architecture → block/warn/info) en tête de la réponse Discord. Timeout HTTP 120s (vs 60s pour `delegate-to-api`) car le reviewer fait 3 appels Anthropic en parallèle.
- **`skills/delegate-to-team/SKILL.md`** : skill "passeur de plat" qui appelle `POST /agents/team/run`. Triggers : `/team <msg>`, "team : …", "équipe dev : …". Affiche `metadata.routed_to` en tête (transparence). Timeout 120s (chaîne complète route + reviewer = ~60s max).
- **`docs/specs/SKILLS.md`** : table des skills mise à jour, nouvelle section "Pont Discord ↔ kisnlab-api" qui explique quand utiliser lequel des 3 `delegate-to-*`.
- **`docs/specs/DISCORD.md`** : exemples d'utilisation enrichis pour `#dev` (3 patterns d'invocation).
- **`docs/specs/LANGGRAPH.md`** : pattern de routing étendu, table des 3 skills passeurs, roadmap Phase 1 cochée.

**Note** : pas de modif `openclaw.json` — les skills sont posés dans `skills/` (bind-mounté sur `/workspace/skills/` côté container). Activation auto au prochain reload OpenClaw. **Pas activé en force** : Mélodie peut tester d'abord en dev.

### Phase 1 — Team supervisor (PR-3/4)

L'agent `team` route une tâche utilisateur vers `dev` ou `reviewer` via un appel Claude Haiku avec `with_structured_output(_Route)`. Pipeline `START → route → delegate → END`.

- **`services/api/app/agents/team.py`** : 2 nodes — `route` (LLM Haiku → `_Route(agent: AgentName)`) + `_make_delegate(dev_graph, reviewer_graph)` (factory qui renvoie le node de délégation). Les sub-graphs sont **injectables** dans `build_team_graph(...)` pour faciliter les tests. Fallback `dev` si l'appel LLM plante (timeout / 5xx Anthropic). Trace Langfuse `run_name=team_router`.
- **`services/api/app/routers/agents.py`** : endpoint `POST /agents/team/run`. `team_graph = build_team_graph(dev_graph=dev_graph, reviewer_graph=reviewer_graph)` réutilise les singletons existants (pas de double compilation). Retourne `metadata={"routed_to": "dev"|"reviewer"}`. `ValueError` propagée par le sub-graph reviewer (parse PR ref) → `422`.
- **Prompt routeur** : système court explicitant les 2 sous-agents et la **règle de fallback** (« si la tâche n'évoque pas explicitement une PR à reviewer, route vers `dev` »).
- **Tests** : 72 verts + 7 skipped (dev + team integration). `test_team_agent.py` :
  - **8 unit tests** : dispatch dev/reviewer, prompt + run_name, fallback erreur LLM, propagation `ValueError`, endpoint 200/422/422-empty.
  - **6 cas paramétrés d'intégration** (skip sans clé) : 2 review (URL + raccourci), 3 dev (refactor / langage / coroutines), 1 ambigu (fallback `dev`). Couvre review/dev/ambigu/fallback comme demandé.
- **Doc** : `LANGGRAPH.md` documente le graphe team.

### Phase 1 — Reviewer 3-perspectives (PR-2/4)

L'agent `reviewer` analyse une PR GitHub sous 3 angles en parallèle (sécurité / qualité / architecture) puis synthétise. Le diff est récupéré une seule fois et envoyé en bloc `cache_control: ephemeral` aux 3 perspectives → cache hit aux calls 2 et 3, ~½ coût Reviewer.

- **`services/api/app/agents/reviewer.py`** : sub-graph `prepare → fan_out (Send) → 3 perspectives parallèles → synthesize`. `_assess()` envoie `SystemMessage` à 2 blocks (préfixe partagé court + diff cached) puis un `HumanMessage` qui injecte le skill markdown spécifique à la perspective. `with_structured_output(_Assessment)` → Claude renvoie `findings` + `severity`. Fallback `severity=info, findings="erreur LLM ..."` si une perspective plante (pas de cascade rouge sur 1 timeout).
- **`services/api/app/agents/state.py`** : `ReviewerState` enrichi de `repo`, `pr_number`, `diff` + reducer `Annotated[list[PerspectiveOpinion], operator.add]` pour merger les écritures parallèles des 3 nodes.
- **`services/api/app/agents/skills/`** : 3 nouveaux fragments markdown — `security_review.md` (secrets, injection, authn/z, crypto), `quality_review.md` (lisibilité, dead code, tests, mutations), `architecture_review.md` (couplage, contrats, breaking changes).
- **Endpoint `POST /agents/reviewer/run`** : retourne `AgentResponse` avec `metadata = {"severities": {"security": "block", ...}, "perspectives_count": 3}`. Erreur de parsing PR ref → `422` (sémantique), pas `500`.
- **Parser PR ref** (`_parse_pr_ref`) : 3 formats — URL `https://github.com/owner/repo/pull/N`, raccourci `owner/repo#N`, narratif `#N (in|of|de|du|dans|sur|on) owner/repo`.
- **Langfuse** : `run_name` distinct par perspective (`reviewer_security`, `reviewer_quality`, `reviewer_architecture`) → 3 traces identifiables côté UI.
- **Tests** : 64 verts + 1 skipped. Nouveaux : `test_reviewer_agent.py` (13 cas — parser, synthesize, metadata, full graph mocké, vérif `cache_control` sur le diff, run_names, fallback erreur LLM, endpoint 200/422). Adaptations `test_state.py` (+2 cas pour les nouveaux champs runtime).
- **Doc** : `LANGGRAPH.md` documente le pipeline reviewer + le pattern de prompt caching.

### Phase 1 — Foundation équipe dev multi-agents (PR-1/4)

Plomberie pour passer de l'agent `dev` solo à l'équipe **Dev + Reviewer**. Aucune feature visible côté API/Discord — refacto pure pour préparer les PRs suivantes (Reviewer en sub-graph, Team supervisor, intégration OpenClaw/Discord).

- **`services/api/app/agents/state.py`** : nouveau module qui centralise les contrats Pydantic. Boundary API (`AgentRequest`, `AgentResponse` avec `metadata: dict` pour porter `routed_to` côté team / `severities` côté reviewer) + states internes LangGraph par graphe (`DevState`, `ReviewerState` avec `PerspectiveOpinion`, `TeamState`).
- **`services/api/app/agents/skills/`** : nouveau dossier de fragments markdown + `_loader.load_skills([...]) -> str` (concat avec séparateur `---`, fail-fast si fragment manquant). Initialise `dev_base.md` et `github_pr_tools.md` extraits du SYSTEM_PROMPT inline.
- **`services/api/app/agents/dev.py`** : `DevState` passe de `TypedDict` à `BaseModel` (validation gratuite, cohérent avec l'API boundary). System prompt composé via `load_skills(("dev_base", "github_pr_tools"))`. `run_name="dev_agent"` conservé pour Langfuse.
- **`services/api/app/routers/agents.py`** : `RunRequest`/`RunResponse` locaux supprimés au profit de `AgentRequest`/`AgentResponse` partagés. La route `POST /agents/dev/run` reste wire-compatible (champ `metadata` ajouté, `agent` et `response` inchangés).
- **Tests** : 50 verts + 1 skipped (intégration Anthropic). Nouveaux : `test_state.py` (10 cas — validation, defaults, severities), `test_skills_loader.py` (7 cas — load, ordre, missing, names invalides). `test_dev_agent.py` adapté à la state shape Pydantic. `test_auth.py` ajusté pour le champ `metadata`.

### Phase C — tracing Langfuse câblé sur l'agent `dev`

L'agent LangGraph `dev` envoie désormais ses traces (LLM calls + tool calls de la boucle ReAct) dans Langfuse v3, projet `KIS'n Code › KIS'n Lab`.

- **`services/api/app/agents/dev.py`** :
  - Ajout d'un `_build_langfuse_callbacks()` défensif (env vars manquantes ou import KO → `[]`, l'agent reste opérationnel sans observabilité).
  - `react_agent.invoke(..., config={"callbacks": _LANGFUSE_CALLBACKS, "run_name": "dev_agent"})` — la trace racine s'appelle donc `dev_agent` côté UI.
- **`services/api/requirements.txt`** : `langfuse==3.14.6` + `langchain==0.3.30` (le SDK Langfuse v3 exige le package `langchain` complet pour son `CallbackHandler`, pas juste `langchain-core`).
- **`docker-compose.yml`** côté `kisnlab-api` :
  - Env vars `LANGFUSE_PUBLIC_KEY/SECRET_KEY` (`.env`) + `LANGFUSE_HOST=http://langfuse-web:3000` (résolution interne, bypass Traefik).
  - `OTEL_EXPORTER_OTLP_TIMEOUT=30000` — le défaut OTel (~1.7 s) est insuffisant face au cold-start de langfuse-web (Next.js).
- **Nouveau service `minio` (+ `minio-init`)** : Langfuse v3 OTEL ingest exige un blob storage S3-compatible (toutes les configs `LANGFUSE_S3_EVENT_UPLOAD_*=disabled` étaient en réalité ignorées en v3 → 500 sur ingest). MinIO local résout ça : bucket `langfuse`, healthcheck `mc ready`, bind mount `./volumes/minio`. `minio-init` est un one-shot idempotent (`mc mb --ignore-existing`).
- **`langfuse-web` + `langfuse-worker`** : `LANGFUSE_S3_EVENT_UPLOAD_ENABLED=true`, bucket `langfuse`, endpoint `http://minio:9000`, `FORCE_PATH_STYLE=true`, creds `MINIO_ROOT_*`. `LANGFUSE_S3_MEDIA_UPLOAD_ENABLED` reste `false` (l'agent dev n'envoie pas de média).
- **`.env`** : ajout `MINIO_ROOT_USER` + `MINIO_ROOT_PASSWORD` (32 chars, généré).
- **Tests** : 34 tests verts (aucun changement de signature). L'init Langfuse étant défensif, les tests qui n'ont pas les env vars ne tentent pas l'import.
- **Validation E2E** : `POST /agents/dev/run` → 3 traces `dev_agent` visibles dans `KIS'n Lab`, input/output complets, latence + tokens trackés.

### Relance Langfuse v3 (Phase 2)

`clickhouse`, `langfuse-web` et `langfuse-worker` étaient `Exited` depuis 2026-05-02 09:35 (SIGTERM propre, pas de crash applicatif — vraisemblablement un `compose stop` ou veille machine, jamais relancés). Pas de modif de conf nécessaire :

- `docker compose up -d clickhouse` → healthy en ~10s.
- `docker compose up -d langfuse-web langfuse-worker` → migrations Prisma (390) et ClickHouse à jour, web `Ready`, worker démarre toutes ses queues (ingestion, evals, posthog/mixpanel/blobstorage, data-retention, webhooks…).
- Vérifs : `GET /api/public/health` → `200 {"status":"OK","version":"3.169.0"}` ; `GET /api/public/projects` (auth `LANGFUSE_PUBLIC_KEY/SECRET_KEY`) → renvoie l'org `KIS'n Code` + projet `KIS'n Lab`. Clés API toujours valides, prêtes pour le câblage Phase C (tracing `kisnlab-api`).

### Câblage des tools GitHub PR côté agent `dev`

L'agent LangGraph `dev` peut désormais lister, lire et reviewer les PRs via la GitHub App `kisnlab-dev` provisionnée plus tôt dans la journée.

- **Nouveau package `services/api/app/agents/tools/`** :
  - `github_app.py` : charge les credentials (`/secrets/<app>.{env,pem}` → fallback env vars), signe le JWT RS256, échange contre installation token, cache 50 min thread-safe.
  - `github_client.py` : client HTTP (httpx) — `list_prs`, `get_pr`, `get_pr_diff`, `review_pr`, `comment_pr`. Pas de checkout local : tout passe par l'API GitHub.
  - `github_tools.py` : 5 tools LangChain (`@tool`) — `gh_pr_list`, `gh_pr_get`, `gh_pr_diff`, `gh_pr_review`, `gh_pr_comment`. Diff tronqué à 60 k chars pour rester dans le budget contexte.
- **Agent `dev.py` recâblé** sur `create_react_agent` (boucle ReAct) avec les 5 tools ; signature `{"task", "response"}` préservée pour le router et les tests existants.
- **`docker-compose.yml`** : volumes read-only `/secrets/kisnlab-dev.{env,private-key.pem}` montés sur `kisnlab-api`, `GH_APP_NAME=kisnlab-dev` ajouté.
- **Scope volontairement réduit** : pas de `gh_pr_create` ni `git_push` aujourd'hui — KIS oblige, on les ajoutera quand un agent aura un déclencheur concret pour produire du code à merger.
- **Tests** : 21 nouveaux tests unitaires (httpx mocké) — 99 % de couverture sur les modules ajoutés.
- **Specs** : `docs/specs/GITHUB_BOT.md` mis à jour (section "Tools côté agent" + section "Secrets dans le container").

### Identité bot pour l'agent `dev` — GitHub App `kisnlab-dev`

Provisionnement d'une seconde GitHub App pour l'agent LangGraph `dev` (`services/api/app/agents/dev.py`), suivant la convention `kisnlab-<agent>` actée juste avant.

- **App `kisnlab-dev`** : créée côté `@kisnco`, App ID `3643429`, Installation ID `130547284`. Mêmes permissions que `kisnlab-claude-code` (Contents/PRs/Issues/Workflows R+W, Metadata R). Installée sur **All repositories**. Permet review entre agents (le bot dev peut review les PRs ouvertes par Claude Code et inversement).
- **Plomberie** : aucun changement de code — les scripts `gh-app-token.sh` et `gh-app-bot.sh` étaient déjà génériques via `GH_APP_NAME`. Secrets ajoutés dans `~/.claude/secrets/kisnlab-dev.{env,private-key.pem}`.
- **Usage** : `GH_APP_NAME=kisnlab-dev ./scripts/gh-app-bot.sh ...`
- **Spec mise à jour** : `docs/specs/GITHUB_BOT.md` (section App + tableau des agents).

**Note** : l'agent `dev` tourne dans le container `kisnlab-api`, qui n'a pas accès à `~/.claude/secrets/`. Quand l'agent gagnera des tools git/gh (Phase ultérieure), choisir entre volume mount du `.pem` ou injection via env vars (`GH_APP_PRIVATE_KEY` multi-ligne). Aujourd'hui, le bot est uniquement utilisable depuis le terminal local de Mélodie pour préparer le terrain.

### Identité bot pour les agents IA — GitHub App `kisnlab-claude-code`

Mise en place d'une identité dédiée pour les PRs ouvertes par Claude Code, afin de permettre l'approbation par un humain (impossible si auteur = self avec branch protection) et préparer un modèle multi-agents.

- **Choix d'archi** : GitHub App (vs bot user) — pas de siège org, tokens 1h auto-renouvelés, permissions fines, modèle scalable (1 App par agent).
- **App `kisnlab-claude-code`** : créée côté `@kisnco`, App ID `3643047`, Installation ID `130539343`. Permissions : Contents/PRs/Issues/Workflows R+W, Metadata R. Webhooks désactivés. Installée sur **All repositories** (5 repos kisnco couverts).
- **Plomberie locale** :
  - Secrets dans `~/.claude/secrets/` (chmod 700), `.env` + `.private-key.pem` (chmod 600).
  - `scripts/gh-app-token.sh` : génère un installation token via JWT RS256 signé (durée ~1h).
  - `scripts/gh-app-bot.sh` : wrapper unique avec sous-commandes `push`, `pr-create` (auto-label `claude-generated`), `exec`, `token`. Convertit l'origin SSH en HTTPS+token à la volée sans toucher la config locale.
- **Spec créée** : `docs/specs/GITHUB_BOT.md` (archi, secrets, scripts, usage, rotation, ajout d'un nouvel agent).

**Décisions** :
- 1 App par agent (`kisnlab-<agent>`) → identité distincte sur chaque PR pour traçabilité multi-agents.
- Auteur des commits reste l'humain — le bot ne change que le pushers et le PR opener.
- Scripts génériques (`GH_APP_NAME` paramétrable) pour basculer facilement entre Apps.

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
