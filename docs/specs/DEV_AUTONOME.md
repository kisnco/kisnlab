# DEV_AUTONOME.md — Boucle de développement autonome

_Source de vérité pour l'agent dev autonome de KisnLab (Phase 3)._

> **Statut : conception.** Aucune ligne de code écrite. Ce document fige
> l'architecture et le découpage avant implémentation. Les questions ouvertes
> en fin de document doivent être tranchées au fil des PRs.

---

## Rôle

Transformer une demande exprimée en langage naturel sur Discord (« implémente
telle fonctionnalité ») en une **pull request prête à merger**, produite de
façon autonome par les agents : l'agent `dev` code, l'agent `reviewer` review,
ils itèrent ensemble jusqu'à convergence. **Seule Mélodie merge.**

C'est la suite logique de la Phase 1 (équipe Dev + Reviewer) et de la Phase 2
(mémoire conversationnelle).

---

## Vision — la boucle

```
Discord : « implémente <besoin> »
        │
        ▼
  create_issue        → crée une issue GitHub formatée en user story
        │
        ▼
  code  ◄──────────────────────┐  le runner invoque le moteur de codage :
   │ │                         │  écrit, lance les tests, debug en autonomie
   │ └─ besoin d'info ─→ ask_reviewer ──┐  le moteur peut poser une question
   │                                    │  au reviewer (fil de commentaires
   │ ◄──────────────────────────────────┘  de la PR) puis reprendre
   ▼                           │
  push                         │  1ᵉʳ tour : crée la PR
   │                           │  tours suivants : pousse un commit sur la
   ▼                           │  MÊME branche → la PR se met à jour
  review                       │  le reviewer review le nouveau diff
   │                           │  ET poste sa review sur la PR
   ▼                           │
  decide                          trois issues possibles :
   │
   ├─ REQUEST_CHANGES ───→ reboucle sur `code` avec le feedback (si ≤ 4 retours)
   │
   ├─ > 4 retours sans accord ───→ escalate ───→ Mélodie tranche sur Discord
   │                                  (décision prépondérante ; sa directive
   │                                   → `code`, ou « c'est bon » → FIN)
   │
   └─ APPROVE ───→ FIN — PR prête, en attente du merge manuel de Mélodie
```

**La PR n'est créée qu'une seule fois.** Chaque itération suivante = un commit
poussé sur la branche existante ; la PR se met à jour et le reviewer re-review
le nouveau diff. Pas de PR jetée / recréée.

---

## Principe directeur — wrapper, ne pas reconstruire

**Décision (2026-05-16) : on réutilise un outil de codage existant et éprouvé.**

LangGraph reste l'**orchestrateur** : il gère la boucle, les transitions, les
gates, le budget. Il ne code pas. Le travail de codage (écrire, tester, debugger)
est délégué à **Codex** (l'agent de codage CLI d'OpenAI), invoqué comme moteur
dans un workspace isolé. Voir le § « Choix du moteur ».

Rationale : reconstruire un agent codant fiable (écriture multi-fichiers, debug,
exécution de tests) est un chantier de plusieurs mois pour un résultat médiocre.
Des outils battle-tested le font déjà. Cohérent avec la règle « Recherche &
Réutilise » et la philosophie KIS.

---

## Architecture

### Vue d'ensemble

```
Discord ──→ kisnlab-dev-bot ──→ kisnlab-api (graphe LangGraph « dev autonome »)
                                      │
                          ┌───────────┼────────────┐
                          ▼           ▼            ▼
                   outils GitHub  kisnlab-dev-  sous-graphe
                   (App kisnlab-  runner        reviewer
                    dev)          (workspace +  (existant,
                                   moteur de     + post review)
                                   codage)
```

### Le graphe orchestrateur (LangGraph)

Nouveau graphe dans `services/api/app/agents/` (provisoire : `autonomous_dev.py`).

| Node | Rôle |
|---|---|
| `create_issue` | Reformule la demande Discord en issue GitHub (user story). |
| `code` | Le runner invoque le moteur de codage. Sortie : un diff prêt à pousser **ou** une question pour le reviewer. |
| `ask_reviewer` | Si le moteur a posé une question : le reviewer y répond (fil de commentaires de la PR), puis retour à `code`. |
| `push` | 1ᵉʳ tour : ouvre la PR (**base = `dev`**). Tours suivants : pousse un commit sur la même branche → la PR se met à jour. |
| `review` | Le sous-graphe reviewer analyse le nouveau diff et **poste** sa review. |
| `decide` | `APPROVE` → `END`. `REQUEST_CHANGES` → `code` (avec feedback) si ≤ 4 retours. Au-delà de 4 retours sans accord → `escalate`. |
| `escalate` | Synthétise le désaccord (point de blocage + position du moteur + position du reviewer + lien PR), poste sur Discord et **interrompt** le graphe en attendant l'arbitrage de Mélodie. |

Edges conditionnels : après `code`, route vers `ask_reviewer` (question) ou
`push` (diff prêt) ; après `decide`, route vers `code` (reboucle), `escalate`
(plafond) ou `END` (`APPROVE`) ; après `escalate`, route vers `code` (directive
de Mélodie) ou `END` (elle clôt).

État Pydantic dédié (`AutonomousDevState`) : `task`, `issue`, `branch`,
`pr_number`, `iteration`, `review_feedback`, `pending_question`,
`human_directive`, `status`.

> **Checkpointer persistant requis.** Le node `escalate` met le run en pause
> (`interrupt` LangGraph) pendant un délai humain potentiellement long. Un
> checkpointer in-memory (`MemorySaver`) perdrait le run en cas de redémarrage
> de `kisnlab-api` — le graphe « dev autonome » utilise donc **`PostgresSaver`**
> (persistance déjà disponible via Postgres).

### Le runner — workspace d'exécution

Nouveau service Docker **`kisnlab-dev-runner`** (même logique de séparation que
`kisnlab-dev-bot` : un service = une responsabilité).

- Expose une interface HTTP minimale (`POST /run`) appelée par le node `code`.
- Embarque le moteur de codage + les runtimes (Python, Node…) + un navigateur
  headless pour l'E2E web. **Image pré-buildée, dépendances déjà installées.**
- **Réseau isolé** (`dev-runner-net`), sans accès à `postgres` / `redis` —
  même posture que `openclaw-dind`.

**Workspace : clone persistant, branche jetable.** Le repo est cloné **une
seule fois** dans `./volumes/dev-workspace/<repo>/` ; il reste en place entre
les runs (dépendances installées conservées). À chaque run, on remet l'état à
zéro **sans re-cloner** :

```
git fetch origin
git checkout -b <type>/<slug-issue> origin/dev   # branche de travail, depuis dev
git clean -fdx                                   # repart d'un arbre propre
```

La branche de travail part de **`dev`** (branche d'intégration du projet) et
suit la convention de nommage du repo (`feat/…`, `fix/…`, `docs/…`). Une
request = une branche = une PR ; les itérations de la boucle restent sur cette
branche.

> **Pourquoi pas un workspace détruit/recréé à chaque run ?** Re-cloner coûte
> du temps et de l'I/O — pas des tokens (les tokens = ce que le modèle *lit*).
> Le `reset` ci-dessus garantit un état propre sans le coût du re-clone. Le coût
> en tokens (exploration du code par le moteur) se maîtrise via le **prompt
> caching** : le contexte repo lu une fois est servi depuis le cache.
> La construction est **entièrement scriptée** — jamais de montage manuel.

> **Pas besoin de Docker-in-Docker.** Lancer `pytest` / `npm test` / Playwright
> ne demande que les runtimes dans l'image du runner. La DinD ne serait requise
> que si un projet testé orchestre lui-même des containers — hors périmètre V1.
> On évite ainsi l'instabilité DinD sur macOS notée dans `STACK.md`.

### Le moteur de codage (wrappé)

Le runner invoque **Codex** en mode **non-interactif** (`codex exec`), dans le
workspace, avec : l'issue (user story) en tâche initiale, ou le feedback du
reviewer aux itérations suivantes. L'auth se fait via le compte ChatGPT — cf.
§ « Choix du moteur ».

### Outils GitHub

L'App **`kisnlab-dev`** a déjà les permissions nécessaires (`Contents` /
`Pull requests` / `Issues` en R+W — cf. `GITHUB_BOT.md`). Outils à ajouter
côté `tools/github_tools.py` :

| Outil | Rôle |
|---|---|
| `gh_issue_create` | crée l'issue user story |
| `gh_pr_create` | ouvre la PR depuis la branche de travail |
| `gh_pr_update` | met à jour la PR (nouveaux commits poussés) |

Le push de branche se fait avec le token de l'App (logique de
`scripts/gh-app-bot.sh`, à porter côté Python).

### Communication Dev ↔ Reviewer

Le sous-graphe `reviewer` existant est réutilisé. L'échange est **bidirectionnel**,
le **fil de commentaires de la PR** sert de canal commun et traçable :

- **Reviewer → Dev** : le reviewer **poste sa review** sur la PR via `gh_pr_review`
  (`APPROVE` / `REQUEST_CHANGES` / `COMMENT`). Le moteur la lit au tour suivant.
- **Dev → Reviewer** : si le moteur de codage bloque (besoin d'une précision sur
  l'intention, un choix d'archi, une ambiguïté de l'issue), il pose une question
  en commentaire de PR ; le node `ask_reviewer` y fait répondre le reviewer, puis
  le moteur reprend. Ils dialoguent jusqu'à converger sur la meilleure solution.

> Ça ne contredit pas la règle Phase 1 « pas d'auto-post ». Cette règle visait
> l'auto-post sur **Discord**, pour ne pas spammer une conversation. Ici, le fil
> de la **PR** EST le canal de communication Dev ↔ Reviewer de la boucle. C'est
> l'usage prévu, et la PR reste protégée : seul le merge humain est bloquant.

### Arbitrage humain (escalade)

Les agents peuvent ne pas converger. **Au-delà de 4 retours Dev ↔ Reviewer sans
`APPROVE`**, le node `escalate` met Mélodie dans la boucle plutôt que d'arrêter
sèchement :

1. Il **synthétise le blocage** : le point de désaccord, la dernière position
   du moteur de codage, la dernière review du reviewer, le lien de la PR.
2. Il **poste cette synthèse sur Discord** et **interrompt** le run (`interrupt`
   LangGraph — le run reste en pause, persisté).
3. Mélodie **tranche**. Sa décision est **prépondérante** — elle l'emporte sur
   les deux agents. Elle s'appuie sur leurs arguments (qu'elle voit dans la
   synthèse) mais n'y est pas liée.
4. Selon sa réponse, le graphe reprend : sa directive est injectée dans `code`
   (reboucle), ou elle clôt le run (« c'est bon » / abandon → `END`).

Principe : **autonomie tant que ça converge, humain dès que ça bloque.** Mélodie
n'est jamais bloquante sur un run qui se passe bien, toujours décisionnaire sur
un run qui patine.

### Tests & E2E web

- **Tests unitaires / lint** : le moteur de codage les lance lui-même dans le
  workspace et corrige jusqu'au vert (comportement natif de Codex).
- **E2E web** : pour les projets web (Kis'n Way, site KIS'n Code), le runner
  embarque Playwright + Chromium headless ; le moteur écrit et exécute des
  parcours utilisateur. Livré en dernière PR de la phase.

---

## Contexte & mémoire de l'agent

Le mot « mémoire » recouvre **quatre couches distinctes** — à ne pas confondre :

| Couche | Quoi | Où | Cycle de vie |
|---|---|---|---|
| **Code** | le code source du repo | workspace (clone) | éphémère / run · prompt caching |
| **Connaissance projet** | specs, archi, conventions | `docs/` + `CLAUDE.md`, **versionnés** | permanent, évolue avec le code |
| **Apprentissage** | pièges, bugs résolus | `LESSONS.md` + tests de non-régression | permanent (cf. § suivant) |
| **Conversationnelle** | historique d'un run | checkpointer `PostgresSaver` | par run |

### Connaissance projet : documentation versionnée, pas de base vectorielle

L'agent traite la documentation versionnée du repo cible comme un **contrat de
travail** :

1. **Début de run** — il lit `docs/` + le fichier de contrat (`AGENTS.md`, que
   Codex lit nativement) + `LESSONS.md` → contexte injecté.
2. **Pendant** — il code en respectant ces conventions.
3. **Avant la PR** — il met à jour la doc impactée (spec du composant, CHANGELOG).
   La mise à jour de la doc fait **partie du diff de la PR**.
4. **Review** — le reviewer vérifie que la doc suit le code (perspective qualité).

L'agent honore la convention de documentation **du repo cible** — il n'impose
pas la structure de KisnLab.

> Codex lit nativement `AGENTS.md`. KisnLab a aujourd'hui un `CLAUDE.md` — on
> ajoutera un `AGENTS.md` à la racine (reprenant le même contrat) lors du setup
> P3.1, et idem pour les autres repos confiés à l'agent.

> **Décision : documentation markdown versionnée, PAS Postgres + pgvector.**
>
> | | Docs markdown versionnés | Postgres + pgvector |
> |---|---|---|
> | Versionné avec le code | ✅ un commit = code + doc cohérents | ❌ désync possible |
> | Lisible / diffable par un humain | ✅ | ❌ embeddings opaques |
> | Infra | aucune | base vectorielle à maintenir |
> | Récupération | lecture directe, exacte | similarité sémantique, peut rater |
>
> pgvector résout la recherche sémantique sur **gros volume non structuré** —
> pas le besoin ici : un `docs/` structuré se lit directement. Cohérent avec la
> décision archi **Q2 du projet** (« embeddings désactivés en V1, mémoire
> markdown uniquement »). pgvector resterait pertinent si le volume de
> connaissance explosait — pas en V1.

---

## Non-régression & apprentissage

**Un bug résolu ne doit pas revenir.** Deux mécanismes complémentaires :

### Tests de non-régression (mécanisme principal)

Tout bug corrigé par l'agent **doit** s'accompagner d'un test qui :

1. échoue sur le code buggé (reproduit le bug),
2. passe une fois le correctif appliqué.

Ce test est committé avec le fix. La suite de tests devient une **mémoire
exécutable** : le bug ne peut plus réapparaître sans être immédiatement rattrapé.
C'est cohérent avec la règle TDD du projet (RED → GREEN → refactor) et c'est le
garde-fou le plus fiable — il ne dépend pas de la « bonne volonté » du modèle.

Le node `decide` **vérifie** qu'un test de non-régression accompagne tout fix
de bug avant d'autoriser l'approbation.

### Journal des leçons

Un fichier versionné — `docs/specs/LESSONS.md` — recense les **pièges récurrents
et patterns d'erreurs** non triviaux (ex. « le state LangGraph Pydantic exige un
partial dict », « ne pas muter en place »). Le moteur de codage le **lit en début
de run** (injecté dans son contexte) et l'**enrichit** quand il résout un bug
instructif. C'est la mémoire « pédagogique » qui complète les tests : les tests
empêchent la régression, le journal évite de refaire la même erreur ailleurs.

---

## Choix du moteur : Codex

**Décision (2026-05-16) : le moteur de codage est Codex (CLI d'OpenAI).**

| Critère | Claude Code (Anthropic) | Codex (OpenAI) |
|---|---|---|
| Invocation non-interactive | `claude -p`, `--output-format json` | `codex exec` |
| Mode non-surveillé | `--permission-mode acceptEdits` + allowlist | sandbox `workspace-write` / `--full-auto` |
| Lecture du contrat projet | `CLAUDE.md` natif | `AGENTS.md` natif |
| **Coût pour KisnLab** | **API au token uniquement** pour un usage automatisé — facturation à l'usage, récurrente | **inclus dans l'abonnement ChatGPT Plus** déjà payé — coût marginal forfaitaire |

**Facteur décisif : le coût.** Une boucle de dev autonome consomme beaucoup de
tokens (le node `code` surtout, sur plusieurs itérations). Codex est inclus dans
l'abonnement ChatGPT Plus de Mélodie et s'utilise en mode headless via la CLI
(connexion compte ChatGPT). Claude Code, pour un usage automatisé/headless,
imposerait l'API Anthropic au token — coût récurrent significatif pour une TPE.

La cohérence de stack (Claude Code = même fournisseur que le Reviewer) est un
confort d'ops réel mais **mineur face à un écart de coût récurrent**. Le Reviewer
et l'orchestrateur LangGraph **restent sur l'API Claude** (Haiku, faible volume
de tokens, prompt caching) — seul le moteur du node `code` est Codex. Stack
mixte, proprement séparée.

**Auth Codex en container** : connexion une fois en interactif (compte ChatGPT) ;
le fichier d'auth résultant est monté en lecture seule dans `kisnlab-dev-runner`
— même pattern que les secrets GitHub App montés dans `kisnlab-api`.

---

## Gates & sécurité

| Garde-fou | Règle |
|---|---|
| **Merge** | **Humain uniquement** (Mélodie). Branch protection « require approval » déjà en place. |
| **Workspace** | Clone persistant remis à zéro par run (branche jetable), réseau isolé, aucun accès aux secrets de la stack. |
| **Auto-approve du moteur** | Activé **uniquement** dans le sandbox jetable, via allowlist d'outils explicite. |
| **Plafond d'itérations** | Boucle Dev ↔ Reviewer plafonnée à **4 retours**. Au-delà sans accord → `escalate` : Mélodie tranche (cf. § Arbitrage humain). |
| **Budget** | Coût € par run plafonné, tracé Langfuse. Dépassement → arrêt + rapport. |
| **Non-régression** | Tout fix de bug doit être accompagné d'un test de non-régression — vérifié par `decide` avant approbation. |
| **Périmètre repos** | V1 : **KisnLab uniquement**. Code client = décision séparée. |

---

## Découpage en phases / PRs

| PR | Contenu | Livrable |
|---|---|---|
| **P3.0** | Ce document de conception. | spec only |
| **P3.1** | Service `kisnlab-dev-runner` + workspace. Le moteur de codage clone un repo, code une tâche et lance les tests. Endpoint `/run`. **Pas encore de GitHub.** Prouve le wrapping. | runner fonctionnel |
| **P3.2** | Boucle GitHub : nodes `create_issue` + `push`, outils `gh_issue_create` / `gh_pr_create` / push de commits avec token App. | issue + PR auto |
| **P3.3** | Boucle Dev ↔ Reviewer : graphe cyclique sur `PostgresSaver`, reviewer qui poste, node `ask_reviewer` (dialogue bidirectionnel), node `decide`, node `escalate` (arbitrage Discord via `interrupt`), plafond 4 retours + budget, vérif test de non-régression, `LESSONS.md`. | boucle complète |
| **P3.4** | E2E web : Playwright + Chromium dans le runner, parcours utilisateur sur les projets web. | E2E web |

Chaque PR est mergeable indépendamment et apporte une valeur testable.

---

## Risques & questions ouvertes

**Risques**

- **Coût** — le moteur `code` (Codex) tourne sur l'abonnement ChatGPT Plus
  (forfaitaire) ; le Reviewer sur l'API Claude Haiku (faible volume). Risque
  maîtrisé — le plafond d'itérations + budget restent des garde-fous.
- **Qualité du moteur** sur des tâches réelles — à valider sur les premiers runs P3.1.
- **Sécurité de l'exécution autonome** — atténuée par le workspace isolé jetable.
- **Matériel** — MacBook Pro Intel 2019 limité pour des runs longs ; la V2 Mac
  mini M4 Pro (juin 2026) sera plus confortable.

**Questions ouvertes**

1. **Identité GitHub des PRs** : ouvrir les PRs sous `kisnlab-dev[bot]` (App
   existante) ou créer l'App dédiée `kisnlab-codex` (déjà anticipée dans
   `GITHUB_BOT.md`).
2. **Budget € par run** — montant exact à caler en P3.3 (le plafond d'itérations est fixé à 4).
3. **Déclenchement** : comment Mélodie lance un run depuis Discord
   (`@Dev implémente …` ? commande dédiée ?).
4. **Périmètre** : autoriser l'agent sur du code client, ou KisnLab seulement ?

---

## Dépendances

| Composant | Phase | Usage |
|---|---|---|
| `kisnlab-dev-runner` | P3.1 | Workspace + moteur de codage Codex |
| Abonnement ChatGPT Plus | P3.1 | Auth Codex (fichier d'auth monté dans le runner) |
| App GitHub (`kisnlab-dev` ou `kisnlab-codex`) | P3.2 | Issues / PRs / push (cf. question ouverte n°1) |
| Sous-graphe `reviewer` | P3.3 | Review postée sur la PR |
| `PostgresSaver` (LangGraph) | P3.3 | Checkpointer persistant — survie des runs en pause sur `escalate` |
| Langfuse | toutes | Traçage coût + itérations |
| Playwright / Chromium | P3.4 | E2E web |
