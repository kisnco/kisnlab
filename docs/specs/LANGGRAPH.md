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
| **commercial** | Prospects, devis, suivi client | (à définir) | F | `POST /agents/commercial/run` |
| **admin** | Compta SASU, juridique, factures | (à définir) | F | `POST /agents/admin/run` |
| **comm** | Contenu, réseaux, LinkedIn | (à définir) | F | `POST /agents/comm/run` |
| **supervisor** | Routing vers le bon agent selon intent | (à définir) | F | `POST /agents/supervisor/run` |

---

## Graphe `dev` (V1)

```
START → call_claude → END
```

État :
```python
class DevState(TypedDict):
    task: str       # tâche utilisateur en français
    response: str   # réponse Claude
```

Système prompt : positionne l'agent en bras technique KIS'n Code (français, code anglais, KIS, concis).

> 1 seul node en V1 — extensible vers `intent → tool_use → call_claude` quand des tools (lecture repo, run tests, etc.) seront ajoutés.

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
- [ ] Phase C — Tracing Langfuse + historique en mémoire (50 derniers)
- [ ] Phase F — `commercial` / `admin` / `comm` + supervisor + pattern draft Discord
- [ ] Plus tard — tools (lecture repo, run tests, gh CLI), checkpoints Postgres
