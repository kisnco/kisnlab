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
