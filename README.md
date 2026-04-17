# 🦞 KisnLab — Stack IA locale

Stack agentique complète pour piloter ta SASU depuis Discord.

**OpenClaw** (agent conversationnel) + **n8n** (workflows) + **Postgres** (data) + **Langfuse** (coûts)

---

## 📁 Structure du projet

```
kisnlab/
├── docker-compose.yml
├── .env.example              → copie en .env et remplis
├── .gitignore
├── README.md
├── config/
│   ├── openclaw/
│   │   ├── openclaw.json     → config LLM router + Discord
│   │   └── HEARTBEAT.md      → check-list proactive 30min
│   └── postgres/
│       └── init-multiple-dbs.sh
├── skills/                   → tes "agents" en Markdown
│   ├── dev-reviewer/
│   ├── dev-architect/
│   ├── commercial-devis/
│   ├── admin-facturation/
│   ├── comm-linkedin/
│   └── strategie-conseiller/
└── workflows/                → exports n8n (versionnables)
```

---

## 🚀 Installation

### Étape 1 — Prérequis

- **Docker Desktop** installé et lancé
- **Compte Anthropic** avec clé API
- **Bot Discord** créé (voir section Discord ci-dessous)

### Étape 2 — /etc/hosts

```bash
sudo nano /etc/hosts
```

Ajoute ces 4 lignes :
```
127.0.0.1   openclaw.kisnlab.local
127.0.0.1   n8n.kisnlab.local
127.0.0.1   langfuse.kisnlab.local
127.0.0.1   traefik.kisnlab.local
```

### Étape 3 — Secrets

```bash
cp .env.example .env
```

Génère les secrets :
```bash
# Postgres password
openssl rand -base64 32

# Redis password
openssl rand -base64 24

# N8N encryption key (ne JAMAIS changer après 1er lancement)
openssl rand -hex 32

# Langfuse secret
openssl rand -base64 32

# Langfuse salt
openssl rand -base64 32
```

Colle chaque valeur dans `.env`.

### Étape 4 — Rends le script exécutable

```bash
chmod +x config/postgres/init-multiple-dbs.sh
```

### Étape 5 — Lance !

```bash
docker compose up -d
```

Première fois : ~5-10 min pour télécharger les images.

---

## 🎮 Setup Discord

### 1. Crée un serveur Discord "KisnLab"

Dans Discord : "+" → Créer un serveur → "Pour moi et mes amis"

### 2. Crée les channels

Crée ces channels texte dans ton serveur :
```
📢 alertes
👩‍💻 dev
💼 commercial
📊 admin
📣 comm
🧭 strategie
📋 briefs
🔍 logs
```

### 3. Crée le bot

1. Va sur https://discord.com/developers/applications
2. "New Application" → nom : **KisnLab Bot**
3. Onglet "Bot" → "Add Bot"
4. Copie le **Token** → colle dans `.env` `DISCORD_BOT_TOKEN`
5. Active ces **Privileged Gateway Intents** :
   - ✅ Server Members Intent
   - ✅ Message Content Intent
6. Onglet "OAuth2" → "URL Generator"
   - Scopes : `bot`
   - Permissions : `Send Messages` + `Read Message History` + `View Channels`
7. Copie l'URL générée → ouvre dans le navigateur → invite le bot dans ton serveur

### 4. Récupère les IDs

Active le **Mode Développeur** dans Discord :
Paramètres utilisateur → Avancé → Mode développeur ✅

Puis :
- Clic droit sur **ton serveur** → "Copier l'identifiant du serveur" → `DISCORD_GUILD_ID`
- Clic droit sur **toi-même** → "Copier l'identifiant" → `DISCORD_YOUR_USER_ID`
- Clic droit sur chaque **channel** → "Copier l'identifiant" → les `DISCORD_CHANNEL_*`

Remplis tout dans `.env`.

---

## 🔗 Accès aux interfaces

| Service | URL | Identifiants |
|---|---|---|
| 🔗 n8n | http://n8n.kisnlab.local | `N8N_USER` / `N8N_PASSWORD` |
| 📊 Langfuse | http://langfuse.kisnlab.local | À créer au 1er login |
| 🦞 OpenClaw | http://openclaw.kisnlab.local | — |
| 🚦 Traefik | http://traefik.kisnlab.local | `TRAEFIK_DASHBOARD_AUTH` |

---

## 📊 Activer Langfuse (Étape 2)

1. Ouvre http://langfuse.kisnlab.local
2. Crée ton compte admin
3. Crée un projet **"KisnLab"**
4. Paramètres → API Keys → génère une paire
5. Ajoute dans `.env` :
   ```
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   ```
6. `docker compose restart openclaw`

---

## 🧪 Premier test

Envoie dans `#dev` sur ton serveur Discord :
```
@KisnLab Bot review ce code : function add(a,b){return a+b}
```

Le bot doit répondre avec une review structurée.

---

## 🛠 Commandes utiles

```bash
# Voir les logs en temps réel
docker compose logs -f openclaw
docker compose logs -f n8n

# Redémarrer un service
docker compose restart openclaw

# Arrêter la stack (données préservées)
docker compose down

# Mettre à jour les images
docker compose pull && docker compose up -d

# Accès Postgres
docker exec -it kisnlab-postgres psql -U kisnlab_admin

# Shell OpenClaw
docker exec -it kisnlab-openclaw sh
```

---

## 💬 Comment utiliser les channels Discord

| Channel | Exemple de message |
|---|---|
| **#dev** | `@bot review le fichier Auth.php` |
| **#dev** | `@bot propose une archi pour [feature]` |
| **#commercial** | `@bot fais un devis pour [brief client]` |
| **#admin** | `@bot génère la facture pour [client] [montant]` |
| **#comm** | `@bot écris un post LinkedIn sur [sujet]` |
| **#strategie** | `@bot dois-je accepter cette mission à [tarif] ?` |
| **#alertes** | ← automatique (n8n + heartbeat) |
| **#briefs** | ← automatique (résumé hebdo n8n) |

---

## ⚠️ Sécurité — avant toute exposition publique

Cette stack est pour du **dev local uniquement**.
Avant de la rendre accessible depuis Internet :

- [ ] Activer HTTPS (Traefik + Let's Encrypt ou Cloudflare Tunnel)
- [ ] Restreindre `allowedUsers` dans `openclaw.json` à ton seul ID Discord
- [ ] Changer tous les mots de passe par défaut
- [ ] Activer 2FA sur n8n
- [ ] Configurer les backups Postgres (Restic + Backblaze B2)
- [ ] Mettre le pare-feu macOS actif

---

## 🆘 Troubleshooting

**"Cannot connect to n8n.kisnlab.local"**
→ Vérifie `/etc/hosts` — les 4 lignes doivent être présentes

**"Postgres ne démarre pas"**
→ `docker compose logs postgres` — souvent un problème de permission sur le script init
→ Solution : `chmod +x config/postgres/init-multiple-dbs.sh`

**"Le bot Discord ne répond pas"**
→ Vérifie que `Message Content Intent` est activé dans le Developer Portal
→ `docker compose logs openclaw` pour voir l'erreur

**"Langfuse ne trace rien"**
→ Les clés `LANGFUSE_PUBLIC_KEY` et `LANGFUSE_SECRET_KEY` doivent être remplies
→ Puis `docker compose restart openclaw`

---

Made with 🦞 pour KisnLab
