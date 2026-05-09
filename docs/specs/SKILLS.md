# SKILLS.md — Skills OpenClaw

_Source de vérité pour tous les agents IA de KisnLab._

---

## Principe

Un skill = un fichier `skills/[nom]/SKILL.md` avec frontmatter YAML.
OpenClaw charge les skills au démarrage depuis `/workspace/skills/`.

### Frontmatter obligatoire

```yaml
---
name: skill-name
description: Une ligne — ce que fait ce skill
channel: dev | commercial | admin | comm | strategie
llm: primary | fast
approval: required   # uniquement si action externe (envoi, publication...)
---
```

---

## Skills livrés

| Skill | Channel | LLM | Approbation | État |
|-------|---------|-----|-------------|------|
| `dev-reviewer` | #dev | Sonnet | Non | ✅ Prêt |
| `dev-architect` | #dev | Sonnet | Non | ✅ Prêt |
| `dev-project-manager` | #dev | Sonnet | Non | ✅ Prêt |
| `github-dashboard` | #dev | Haiku | Non | ✅ Prêt |
| `commercial-devis` | #commercial | Sonnet | ✅ Oui | ✅ Prêt |
| `admin-facturation` | #admin | Sonnet | ✅ Oui | ✅ Prêt |
| `comm-linkedin` | #comm | Haiku | ✅ Oui | ✅ Prêt |
| `strategie-conseiller` | #strategie | Sonnet | ✅ Oui | ✅ Prêt |
| `strategie-veille` | #strategie | Haiku | Non | ✅ Prêt |
| `delegate-to-api` | #dev | Haiku | Non | ✅ Prêt |
| `delegate-to-reviewer` | #dev | Haiku | Non | ✅ Prêt |
| `delegate-to-team` | #dev | Haiku | Non | ✅ Prêt |

---

## Skills à créer (backlog)

### Pôle Dev

| Skill | Description | LLM | Priorité |
|-------|-------------|-----|----------|
| `dev-developer` | Implémente des features selon un brief | Sonnet | P1 |
| `dev-qa` | Génère des tests et scénarios de QA | Sonnet | P2 |
| `dev-doc` | Rédige la documentation technique | Haiku | P3 |

### Pôle Commercial

| Skill | Description | LLM | Priorité |
|-------|-------------|-----|----------|
| `commercial-crm` | Suivi client, notes de réunion, relances | Haiku | P2 |
| `commercial-prospection` | Messages de prospection, scripts d'approche | Sonnet | P2 |

### Pôle Admin

| Skill | Description | LLM | Priorité |
|-------|-------------|-----|----------|
| `admin-compta` | Suivi charges, déclarations, TVA SASU | Sonnet | P1 |
| `admin-juridique` | Clauses contrats, CGV, mentions légales | Sonnet | P1 |
| `admin-fiscalite` | Optimisation fiscale SASU, conseils IS | Sonnet | P2 |

### Pôle Comm

| Skill | Description | LLM | Priorité |
|-------|-------------|-----|----------|
| `comm-blog` | Articles de blog tech / freelance | Haiku | P2 |
| `comm-newsletter` | Newsletter mensuelle KIS'n Code | Haiku | P3 |
| `comm-seo` | Audit SEO, meta, suggestions de mots-clés | Haiku | P3 |

### Pôle Stratégie

| Skill | Description | LLM | Priorité |
|-------|-------------|-----|----------|
| `strategie-pricing` | Analyse et recommandation de tarifs | Sonnet | P2 |
| `strategie-bizdev` | Identification d'opportunités business | Sonnet | P3 |

---

## Pont Discord ↔ kisnlab-api (delegate-to-*)

3 skills routent les tâches Discord vers FastAPI/LangGraph. Tous **passeurs de plat** — pas de raisonnement OpenClaw par-dessus.

| Skill | Endpoint API | Trigger Discord | Quand l'utiliser |
|-------|--------------|-----------------|------------------|
| `delegate-to-api` | `POST /agents/dev/run` | "agent dev : [...]" | Tâche dev claire — aucun surcoût de routage. |
| `delegate-to-reviewer` | `POST /agents/reviewer/run` | `/review <PR>` | Review multi-perspectives sur une PR identifiée. |
| `delegate-to-team` | `POST /agents/team/run` | `/team <msg>` | Pas sûre du sous-agent — laisse le superviseur Haiku décider (+1 call LLM ~0.001¢). |

Format de réponse Discord standardisé :
- `delegate-to-reviewer` affiche en tête le mapping `severities` (security/quality/architecture → block/warn/info).
- `delegate-to-team` affiche en tête `routed_to` (dev | reviewer).
- Tous les 3 rapportent le contenu de l'agent **sans reformatage**.

Voir aussi `LANGGRAPH.md` pour le détail des graphes côté API.

---

## Conventions de rédaction d'un skill

1. **Ton rôle** — qui est cet agent en 2 phrases max
2. **Ce que tu fais** — liste des actions concrètes
3. **Format de sortie** — template exact attendu (avec code block)
4. **Tes principes** — 4-6 règles comportementales non négociables

### Règles

- Rédiger en **français** (les skills s'adressent à l'agent)
- Garder chaque skill **focalisé** — un rôle, pas plusieurs
- Toujours inclure `approval: required` si le skill envoie vers l'extérieur
- Conserver la **cohérence du ton** entre skills d'un même pôle
