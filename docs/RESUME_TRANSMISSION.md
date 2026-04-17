# Résumé de transmission — KisnLab
_À lire par Claude Code avant de démarrer le projet_

---

## Qui je suis

**Développeuse senior & responsable technique — KIS'n Code**
Philosophie : _Keep It Simple, Make It Work_

- Profil hybride : architecte technique · lead dev · accélératrice de projets
- Expertise : Symfony, API-first, Docker, CI/CD, sécurité (ISO 27001, SSO)
- Langages : PHP/Symfony (fort) › JS/TS (fort) › Python (apprentissage)
- Clients : TPE/PME, collectivités, porteurs de projets

---

## Ce qu'on construit : KisnLab

**KisnLab** est ma stack IA personnelle auto-hébergée.
Elle me permet de piloter toute mon activité KIS'n Code depuis **Discord**
via des agents IA spécialisés par pôle métier.

### Pourquoi Discord ?
Discord = serveur avec plusieurs channels → un channel par pôle.
Je parle au bot dans le bon channel, il sait quoi faire et quel agent appeler.

---

## L'architecture (décisions validées)

### Deux outils qui se complètent

| Outil | Rôle | Pourquoi |
|---|---|---|
| **OpenClaw** | Agent conversationnel (Discord) | Je pilote en langage naturel, mémoire long terme, proactivité |
| **n8n** | Workflows déterministes | CRON, webhooks, automatisations répétables et fiables |

OpenClaw et n8n communiquent par **webhooks HTTP**.
Chacun orchestre son paradigme — pas de doublon.

### Stack Docker complète

```
🦞 OpenClaw           → agent IA Discord (canal de pilotage)
🔗 n8n                → workflows automatisés (CRON, webhooks)
🐘 Postgres 16        → base unifiée relationnelle + vectorielle (pgvector)
🧠 Redis 7            → queue et cache pour n8n
📊 Langfuse           → observabilité LLM (coûts, tokens, traces)
🚦 Traefik            → reverse proxy, routing par domaine local
```

### LLM Router (économies)

```
Claude Sonnet 4  → tâches critiques (archi, review, conseil, juridique) — 20% des appels
Claude Haiku     → tâches simples (résumés, rédaction, formatage)       — 80% des appels
```

Ollama local prévu sur **Mac mini M4 Pro** (achat prévu juin 2026, après WWDC).

### Domaines locaux (dev MacBook)

```
openclaw.kisnlab.local
n8n.kisnlab.local
langfuse.kisnlab.local
traefik.kisnlab.local (auth requise)
```

---

## Organisation Discord — Le cockpit

```
📢 #alertes      ← heartbeat OpenClaw + n8n (lecture seule)
👩‍💻 #dev          ↔ commandes dev         → Claude Sonnet
💼 #commercial   ↔ devis, CRM             → Claude Sonnet
📊 #admin        ↔ facturation, compta    → Claude Sonnet
📣 #comm         ↔ LinkedIn, blog         → Claude Haiku
🧭 #strategie    ↔ décisions              → Claude Sonnet
📋 #briefs       ← résumés hebdo n8n (lecture seule)
🔍 #logs         ← traces Langfuse (lecture seule)
```

---

## Skills OpenClaw (agents en Markdown)

### Livrés et prêts

| Skill | Channel | LLM | Validation |
|---|---|---|---|
| `dev-reviewer` | #dev | Sonnet | Non |
| `dev-architect` | #dev | Sonnet | Non |
| `commercial-devis` | #commercial | Sonnet | ✅ Oui |
| `admin-facturation` | #admin | Sonnet | ✅ Oui |
| `comm-linkedin` | #comm | Haiku | ✅ Oui |
| `strategie-conseiller` | #strategie | Sonnet | ✅ Oui |

### À créer (priorités)

```
dev-developer · dev-qa · dev-doc
commercial-crm · commercial-prospection
admin-compta · admin-juridique · admin-fiscalite
comm-blog · comm-newsletter · comm-seo
strategie-veille · strategie-pricing · strategie-bizdev
```

---

## Projets actifs (5 en parallèle)

| Projet | Type | Stack | État |
|---|---|---|---|
| Scoreboard Python | Client | Python | En cours |
| Site KIS'n Code | Perso | À définir | Non démarré |
| App Kis'n Way (alignement) | Perso | React Native | En cours |
| Nouvelle prestation IA | Perso | À définir | Idéation |
| Outil comptabilité SASU | Perso | À définir | Non démarré |

---

## Infrastructure physique

### Aujourd'hui

```
💻 MacBook Pro Intel 2019 (32 Go RAM)  → développement local
☁️  Scaleway PLAY2-MICRO               → DÉDIÉ à l'app Kis'n Way + site KIS'n Code
                                         (ne PAS toucher pour KisnLab)
```

### Plan juin 2026

```
🏠 Mac mini M4 Pro 48 Go (reconditionné ~1200-1500€)
   → production KisnLab 24/7
   → Ollama local (Llama 70B Q4)
   → Langfuse + backups Restic/Backblaze
```

### ⚠️ Point important
Le **PLAY2-MICRO Scaleway est réservé à Kis'n Way et au site KIS'n Code**.
KisnLab tourne en **local sur le MacBook** pendant la phase de développement.
Les deux ne se mélangent pas.

---

## État actuel du projet

### ✅ Fait

- Architecture validée (4 versions, beaucoup de réflexion)
- Choix des outils arrêtés (OpenClaw + n8n, pas CrewAI)
- docker-compose.yml complet et fonctionnel
- .env.example avec toutes les variables
- Config OpenClaw avec LLM router et Discord multi-channels
- 6 skills de base rédigés
- CLAUDE.md + docs/specs/ initialisés (8 specs)
- HEARTBEAT.md configuré

### 🔜 À faire immédiatement

1. Ajouter les domaines dans `/etc/hosts`
2. Remplir `.env` (secrets, Discord IDs, Anthropic key)
3. Créer le serveur Discord + bot (guide dans `docs/specs/DISCORD.md`)
4. `chmod +x config/postgres/init-multiple-dbs.sh`
5. `docker compose up -d`
6. Configurer Langfuse (2ème étape après 1er lancement)
7. Appairer Discord bot et tester dans #dev

### 📋 Backlog (après que ça tourne)

- Créer les 14 skills manquants
- Premier workflow n8n : brief hebdomadaire → #briefs
- Workflow n8n : relance factures → #alertes
- Backup Postgres (Restic + Backblaze B2)
- Préparer le déploiement sur Mac mini (juin 2026)

---

## Structure du projet

```
kisnlab/
├── CLAUDE.md                          ← brief Claude Code
├── docker-compose.yml
├── .env                               ← secrets (ne jamais lire/afficher)
├── .env.example
├── .gitignore
├── README.md
├── config/
│   ├── openclaw/
│   │   ├── openclaw.json              ← config LLM router + Discord
│   │   └── HEARTBEAT.md              ← check-list proactive
│   └── postgres/
│       └── init-multiple-dbs.sh
├── skills/
│   ├── dev-reviewer/SKILL.md
│   ├── dev-architect/SKILL.md
│   ├── commercial-devis/SKILL.md
│   ├── admin-facturation/SKILL.md
│   ├── comm-linkedin/SKILL.md
│   └── strategie-conseiller/SKILL.md
├── workflows/                         ← exports n8n versionnés
└── docs/
    └── specs/
        ├── STACK.md
        ├── DISCORD.md
        ├── OPENCLAW.md
        ├── N8N.md
        ├── DATABASE.md
        ├── SKILLS.md
        ├── PROJETS.md
        └── CHANGELOG.md
```

---

## Règles pour Claude Code

1. Lire le spec concerné dans `docs/specs/` avant toute action
2. Mettre à jour le spec + `CHANGELOG.md` après chaque modification
3. Ne jamais lire ni afficher `.env`
4. Montrer le diff avant de modifier `docker-compose.yml` ou `openclaw.json`
5. Demander si ambigu — une question vaut mieux qu'une erreur
6. Rester minimal : la solution la plus simple qui marche
7. Priorités : ça marche › ça ne casse rien › c'est lisible › c'est élégant
