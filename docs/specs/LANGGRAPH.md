# LANGGRAPH.md — Orchestrateur multi-agents

_Source de vérité pour les graphes LangGraph hébergés dans `kisnlab-api`._

---

## Rôle

LangGraph est l'orchestrateur multi-agents métier de KisnLab. Il vit dans le service `kisnlab-api` (FastAPI). Chaque agent est un graphe d'états compilé exposé via une route HTTP.

---

## Pattern de routing

```
Discord → OpenClaw (skill delegate-to-api) → kisnlab-api → graphe LangGraph → Claude → réponse
```

OpenClaw reste le point d'entrée Discord. Il délègue à FastAPI les tâches métier qui demandent un raisonnement structuré ou plusieurs étapes coordonnées.

---

## Agents disponibles

| Agent | Rôle | Modèle | Phase | Endpoint |
|-------|------|--------|-------|----------|
| **dev** | Tâches techniques (code, debug, refactor, archi) | `claude-haiku-4-5-20251001` | B (V1) ✅ | `POST /agents/dev/run` |
| **reviewer** | Review PR multi-perspectives (security/quality/architecture) | `claude-haiku-4-5-20251001` | 1 (Phase 1) ⏳ | `POST /agents/reviewer/run` |
| **team** | Supervisor — route vers `dev` ou `reviewer` | `claude-haiku-4-5-20251001` | 1 (Phase 1) ⏳ | `POST /agents/team/run` |
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

L'agent `dev` est exempt de cette règle (sortie textuelle, pas d'action externe directe).

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
- [ ] Phase 1 — Équipe Dev + Reviewer (PR-1 ✅ foundation, PR-2/3/4 en cours)
- [ ] Phase 2 — Dev avec tools d'écriture (Codex)
- [ ] Phase F — `commercial` / `admin` / `comm` + pattern draft Discord
- [ ] Plus tard — checkpoints Postgres pour reprises longues
