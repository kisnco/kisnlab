# DISCORD.md — Serveur, channels, bot, permissions

_Source de vérité pour la configuration Discord de KisnLab._

---

## Serveur Discord

- **Nom** : KisnLab (serveur privé, usage solo)
- **Accès bot** : restreint à `DISCORD_YOUR_USER_ID` uniquement (`allowedUsers` dans `openclaw.json`)

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

## Bot Discord — Configuration

### Création du bot

1. [discord.com/developers/applications](https://discord.com/developers/applications)
2. "New Application" → nom : **KisnLab Bot**
3. Onglet "Bot" → "Add Bot" → copier le **Token** → `.env` `DISCORD_BOT_TOKEN`

### Privileged Gateway Intents requis

- ✅ Server Members Intent
- ✅ Message Content Intent

### Permissions OAuth2

Scopes : `bot`
Permissions minimales :
- Send Messages
- Read Message History
- View Channels

### Invitation du bot

Onglet OAuth2 → URL Generator → Scopes + Permissions → ouvrir l'URL → inviter dans le serveur KisnLab.

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
| `#dev` | `@bot review le fichier Auth.php` |
| `#dev` | `@bot propose une archi pour [feature]` |
| `#commercial` | `@bot fais un devis pour [brief client]` |
| `#admin` | `@bot génère la facture pour [client] [montant]` |
| `#comm` | `@bot écris un post LinkedIn sur [sujet]` |
| `#strategie` | `@bot dois-je accepter cette mission à [tarif] ?` |
| `#alertes` | ← automatique uniquement |
| `#briefs` | ← automatique uniquement |
| `#logs` | ← automatique uniquement |

---

## Sécurité

- Le bot ne répond qu'à `DISCORD_YOUR_USER_ID` (configuré dans `openclaw.json` → `allowedUsers`)
- Les channels `#alertes`, `#briefs`, `#logs` sont en `readOnly: true` dans la config
- Les actions sensibles (envoi email, git push, paiement, publication) nécessitent `approval: required`