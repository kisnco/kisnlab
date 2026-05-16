# DISCORD.md — Serveur, channels, bot, permissions

_Source de vérité pour la configuration Discord de KisnLab._

---

## Serveur Discord

- **Nom** : KisnLab (serveur privé, usage solo)
- **Accès** : 2 bots distincts, tous les deux restreints à `DISCORD_YOUR_USER_ID` :
  - **`KisnLab Bot`** (display name **`Kael`** sur le serveur) — OpenClaw, skills généralistes (admin, commercial, comm, stratégie). Allowlist via `allowedUsers` dans `openclaw.json`.
  - **`KisnLab Dev Team`** (display name **`Dev`** sur le serveur) — bot Python dédié (`services/dev-bot/`), forwarde chaque mention à `POST /agents/team/run`. Allowlist en dur dans `main.py` via `DISCORD_YOUR_USER_ID`.

> Les *application names* (Discord Developer Portal) restent `KisnLab Bot` et `KisnLab Dev Team` — ce sont des identités stables. Le *display name* sur le serveur (`Kael`, `Dev`) est cosmétique et peut changer.

---

## Channels et rôles

| Channel | Emoji | Usage | Type | LLM |
|---------|-------|-------|------|-----|
| `#alertes` | 📢 | Heartbeat OpenClaw + alertes n8n | Lecture seule (webhookSource: n8n) | — |
| `#dev` | 👩‍💻 | Code, architecture, review, QA | Interactif | Sonnet |
| `#commercial` | 💼 | Devis, CRM, prospection | Interactif | Sonnet |
| `#admin` | 📊 | Facturation, compta, juridique, fiscalité | Interactif | Sonnet |
| `#comm` | 📣 | LinkedIn, blog, newsletter, SEO | Interactif | Haiku |
| `#strategie` | 🧭 | Décisions, veille, pricing, bizdev | Interactif | Sonnet |
| `#briefs` | 📋 | Résumés hebdo automatiques n8n | Lecture seule (webhookSource: n8n) | — |
| `#logs` | 🔍 | Traces Langfuse filtrées | Lecture seule (webhookSource: langfuse) | — |

---

## Bots Discord — Configuration

### Bot 1 — KisnLab Bot (Kael, OpenClaw)

1. [discord.com/developers/applications](https://discord.com/developers/applications)
2. "New Application" → nom : **KisnLab Bot**
3. Onglet "Bot" → "Add Bot" → copier le **Token** → `.env` `DISCORD_BOT_TOKEN`

### Bot 2 — KisnLab Dev Team (service `kisnlab-dev-bot`)

1. Même portail → "New Application" → nom : **KisnLab Dev Team**
2. Onglet "Bot" → "Add Bot" → copier le **Token** → `.env` `DISCORD_DEV_BOT_TOKEN`

### Privileged Gateway Intents requis (les 2 bots)

- ✅ Server Members Intent
- ✅ Message Content Intent

### Permissions OAuth2 (les 2 bots)

Scopes : `bot`
Permissions minimales :
- Send Messages
- Read Message History
- View Channels

### Invitation des bots

Onglet OAuth2 → URL Generator → Scopes + Permissions → ouvrir l'URL → inviter dans le serveur KisnLab. À faire pour chacun des 2 bots.

---

## Récupérer les IDs

Activer **Mode Développeur** : Paramètres utilisateur → Avancé → Mode développeur ✅

| ID | Comment l'obtenir | Variable `.env` |
|----|------------------|-----------------|
| Guild ID | Clic droit sur le serveur → Copier l'identifiant | `DISCORD_GUILD_ID` |
| Ton User ID | Clic droit sur toi-même → Copier l'identifiant | `DISCORD_YOUR_USER_ID` |
| Channel #dev | Clic droit sur le channel → Copier l'identifiant | `DISCORD_CHANNEL_DEV` |
| Channel #commercial | idem | `DISCORD_CHANNEL_COMMERCIAL` |
| Channel #admin | idem | `DISCORD_CHANNEL_ADMIN` |
| Channel #comm | idem | `DISCORD_CHANNEL_COMM` |
| Channel #strategie | idem | `DISCORD_CHANNEL_STRATEGIE` |
| Channel #alertes | idem | `DISCORD_CHANNEL_ALERTES` |
| Channel #briefs | idem | `DISCORD_CHANNEL_BRIEFS` |
| Channel #logs | idem | `DISCORD_CHANNEL_LOGS` |

---

## Exemples d'utilisation par channel

| Channel | Exemple de message |
|---------|-------------------|
| `#dev` | `@Dev explique ce que fait ce code [...]` → route auto vers `dev` |
| `#dev` | `@Dev review la PR kisnco/kisnlab#42` → route auto vers `reviewer` (3 perspectives) |
| `#dev` | `@Kael review le fichier Auth.php` (skill OpenClaw `dev-reviewer`, snippet collé) |
| `#dev` | `@Kael propose une archi pour [feature]` (skill OpenClaw `dev-architect`) |
| `#commercial` | `@Kael fais un devis pour [brief client]` |
| `#admin` | `@bot génère la facture pour [client] [montant]` |
| `#comm` | `@bot écris un post LinkedIn sur [sujet]` |
| `#strategie` | `@bot dois-je accepter cette mission à [tarif] ?` |
| `#alertes` | ← automatique uniquement |
| `#briefs` | ← automatique uniquement |
| `#logs` | ← automatique uniquement |

---

## Sécurité

- Les **deux bots** ne répondent qu'à `DISCORD_YOUR_USER_ID`. Pour Kael : `openclaw.json` → `allowedUsers`. Pour Dev Team : guard en dur dans `services/dev-bot/main.py`.
- Les channels `#alertes`, `#briefs`, `#logs` sont en `readOnly: true` dans la config
- Les actions sensibles (envoi email, git push, paiement, publication) nécessitent `approval: required` côté skill OpenClaw
- L'agent `dev` est en **lecture seule** sur GitHub (`gh_pr_list` / `gh_pr_get` / `gh_pr_diff`). Aucun outil d'écriture exposé. Si publication souhaitée un jour : skill séparé avec validation explicite.