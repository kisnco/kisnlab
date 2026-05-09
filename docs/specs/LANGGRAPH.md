# LANGGRAPH.md — Orchestrateur multi-agents

_Source de vérité pour les graphes LangGraph hébergés dans `kisnlab-api`._

---

## Rôle

LangGraph est l'orchestrateur multi-agents métier de KisnLab. Il vit dans le service `kisnlab-api` (FastAPI). Chaque agent est un graphe d'états compilé exposé via une route HTTP.

---

## Pattern de routing

```
Discord (@Dev) → kisnlab-dev-bot → kisnlab-api (/agents/team/run)
       → team supervisor (route LLM Haiku) → dev | reviewer → Claude → réponse
```

L'équipe dev a sa propre identité Discord, distincte de Kael (OpenClaw). Le service `kisnlab-dev-bot` (cf. `services/dev-bot/`) écoute uniquement les mentions du bot Dev Team, transmet chaque message à `POST /agents/team/run`, et poste la réponse en thread dans le channel d'origine. Préfixe `[dev]` ou `[reviewer]` selon le routage du superviseur.

Kael (OpenClaw) ne route plus rien vers FastAPI — séparation nette entre les 2 entités. Cf. `DISCORD.md`.

---

## Agents disponibles

| Agent | Rôle | Modèle | Phase | Endpoint |
|-------|------|--------|-------|----------|
| **dev** | Tâches techniques (code, debug, refactor, archi) | `claude-haiku-4-5-20251001` | B (V1) ✅ | `POST /agents/dev/run` |
| **reviewer** | Review PR multi-perspectives (security/quality/architecture) | `claude-haiku-4-5-20251001` | 1 (Phase 1) ✅ | `POST /agents/reviewer/run` |
| **team** | Supervisor — route vers `dev` ou `reviewer` | `claude-haiku-4-5-20251001` | 1 (Phase 1) ✅ | `POST /agents/team/run` |
| **commercial** | Prospects, devis, suivi client | (à définir) | F | `POST /agents/commercial/run` |
| **admin** | Compta SASU, juridique, factures | (à définir) | F | `POST /agents/admin/run` |
| **comm** | Contenu, réseaux, LinkedIn | (à définir) | F | `POST /agents/comm/run` |

---

## Contrats partagés (`app/agents/state.py`)

Chaque endpoint `/agents/*/run` consomme `AgentRequest` et renvoie `AgentResponse` :

```python
class AgentRequest(BaseModel):
    task: str  # 1..8000 chars

class AgentResponse(BaseModel):
    agent: Literal["dev", "reviewer", "team"]
    response: str
    metadata: dict = {}  # team → routed_to ; reviewer → severities/perspectives_count
```

Chaque graphe LangGraph utilise un state Pydantic dédié : `DevState`, `ReviewerState` (+ `PerspectiveOpinion`), `TeamState`. `StateGraph(BaseModel)` est supporté par LangGraph 0.2.60 ; les nodes peuvent retourner soit l'objet entier soit un partial dict.

---

## Skills (`app/agents/skills/`)

Fragments markdown injectés dans les system prompts. API : `load_skills(["dev_base", "github_pr_tools"]) -> str` (concaténation avec séparateur `---`, fail-fast si fragment manquant). Permet de partager la base d'identité entre sous-agents et de versionner les fragments indépendamment du code Python.

---

## Graphe `dev` (V1)

```
START → call_claude → END
```

État : `DevState` (Pydantic — `task`, `response`).

Système prompt composé via `load_skills(("dev_base", "github_pr_tools"))`.

> 1 seul node en V1 — extensible vers `intent → tool_use → call_claude` quand des tools (lecture repo, run tests, etc.) seront ajoutés.

---

## Graphe `reviewer` (Phase 1)

```
START → prepare → (Send fan_out) → assess_security    ┐
                                 → assess_quality    ─┼→ synthesize → END
                                 → assess_architecture┘
```

État : `ReviewerState` (Pydantic — `task`, `repo`, `pr_number`, `diff`, `perspectives` avec reducer `operator.add`, `response`).

**Pattern de coût — prompt caching Anthropic** : `prepare` récupère le diff une seule fois via `gh_pr_diff`. Chaque perspective envoie un `SystemMessage` à 2 blocks :

```python
[
    {"type": "text", "text": REVIEWER_SYSTEM_PREFIX},          # bloc 1, partagé court
    {"type": "text", "text": diff,
     "cache_control": {"type": "ephemeral"}},                  # bloc 2, partagé long
]
```

Le diff étant identique sur les 3 calls, Anthropic le sert depuis le cache aux calls 2 et 3 → coût Reviewer divisé par ~2 sur la portion diff (10x moins cher en cache hit).

Le `HumanMessage` qui suit injecte le skill markdown spécifique (`security_review.md` / `quality_review.md` / `architecture_review.md`) — petit, variable, non caché.

**Fallback** : si une perspective plante (timeout, 5xx Anthropic), elle retourne `severity=info, findings="erreur LLM …"`. Le graphe synthétise quand même avec les 2 autres.

**Tracing Langfuse** : `run_name` distinct par perspective (`reviewer_security`, `reviewer_quality`, `reviewer_architecture`) → 3 traces côté UI Langfuse.

**Endpoint** :

```http
POST /agents/reviewer/run
{ "task": "kisnco/kisnlab#7" }

→ 200 { "agent": "reviewer",
        "response": "# Review …",
        "metadata": { "severities": {"security": "block", …},
                      "perspectives_count": 3 } }
```

Formats de PR ref acceptés : URL GitHub, `owner/repo#N`, narratif `#N (in|of|de|du|dans|sur|on) owner/repo`. Si parse impossible → `422`.

---

## Graphe `team` (Phase 1)

```
START → route → delegate → END
```

État : `TeamState` (Pydantic — `task`, `routed_to: Optional[AgentName]`, `response`).

- **`route`** : Claude Haiku avec `with_structured_output(_Route)` (where `_Route(agent: Literal["dev", "reviewer"])`). Décision déterministe, fallback `dev` si l'appel LLM plante.
- **`delegate`** : invoque le sub-graph ciblé (`dev_graph` ou `reviewer_graph`) avec son state propre (`DevState` / `ReviewerState`). Les sub-graphs sont injectables dans `build_team_graph(dev_graph=..., reviewer_graph=...)` — le router HTTP réutilise les singletons existants pour éviter une double compilation.

**Règle de fallback** (encodée dans le system prompt) : si la tâche ne mentionne pas explicitement une PR à reviewer (URL GitHub / `owner/repo#N` / narratif), route vers `dev`.

**Tracing Langfuse** : `run_name=team_router` sur l'appel de routage. Le sub-graph qui exécute conserve ses propres traces (`dev_agent` ou `reviewer_<perspective>`).

**Endpoint** :

```http
POST /agents/team/run
{ "task": "review kisnco/kisnlab#7" }

→ 200 { "agent": "team",
        "response": "# Review …",
        "metadata": { "routed_to": "reviewer" } }
```

`ValueError` du sub-graph (typiquement reviewer sur une PR ref invalide) → `422`.

---

## Phase 1 — Équipe dev multi-agents (en cours)

Pattern : **hybride** — supervisor au top + fan-out parallèle dans le Reviewer.

```
team supervisor (route LLM Haiku)
   ├── delegate → dev (sub-graph existant)
   └── delegate → reviewer
                     ├── perspective security  ┐
                     ├── perspective quality   │ Send API (parallèle)
                     ├── perspective architecture┘
                     └── synthesize
```

Découpage en 4 PRs :
1. **Foundation** (cette PR) — `state.py` + skills loader + refacto `dev.py`/router. 0 feature visible.
2. **Reviewer** — sub-graph 3 perspectives parallèles via `Send`, prompt caching Anthropic (`cache_control: ephemeral`) sur le diff partagé pour diviser ~2 le coût Reviewer.
3. **Team supervisor** — 2 nodes (`route` avec `with_structured_output(AgentName)` Haiku + `delegate`). Tests routing : ≥ 6 cas (review/dev/ambigu/fallback).
4. **OpenClaw + Discord + doc** — skills `/review <PR>` et `/team <msg>` via `delegate-to-api`.

**Instrumentation Langfuse obligatoire à toutes les PRs** : trace par sous-agent ET par perspective. Fallback SDK direct (`@observe`) si OTel reste bloqué côté Phase C.

---

## Validation envois externes

Règle absolue (cf. `feedback_external_actions.md`) : **aucun agent ne déclenche d'action externe sans validation manuelle**.

Pour les agents qui touchent à l'extérieur (`commercial`, `admin`, `comm`) :
- Sortie = **draft markdown** uniquement
- Publication dans `#admin` ou `#alertes` Discord pour validation
- Exécution réelle = action manuelle ou workflow n8n explicitement déclenché

L'agent `dev` est en **lecture seule** sur GitHub (`gh_pr_list`, `gh_pr_get`, `gh_pr_diff`). Les outils d'écriture (`gh_pr_review`, `gh_pr_comment`) sont définis mais **non exposés** à l'agent — ils restent accessibles à un futur skill avec validation explicite. Cf. `services/api/app/agents/tools/github_tools.py` (constante `GITHUB_PR_WRITE_TOOLS`).

---

## Dépendances

| Composant | Phase | Usage |
|-----------|-------|-------|
| Anthropic API | B | Inference Claude |
| Postgres | C (later) | Persistance exécutions / state checkpoints |
| Redis | F (later) | Queue / pub-sub inter-agents |
| Langfuse | C | Tracing automatique via callback handler |

---

## Modèle V1

- Tous les agents tournent sur **Haiku 4.5** au démarrage (limitation de coût pendant le rodage)
- Bascule **Sonnet 4.x** prévue agent par agent quand prompts stables et qualité validée

---

## Roadmap

- [x] Phase B — Agent `dev` (1 node, Haiku, sans tracing)
- [x] Phase C — Tracing Langfuse via `CallbackHandler` (run_name=`dev_agent`)
- [x] Phase 1 — Équipe Dev + Reviewer (PR-1 → PR-4 ✅)
- [ ] Phase 2 — Dev avec tools d'écriture (Codex)
- [ ] Phase F — `commercial` / `admin` / `comm` + pattern draft Discord
- [ ] Plus tard — checkpoints Postgres pour reprises longues
