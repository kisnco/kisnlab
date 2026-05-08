# GitHub Bot — Identité automation des agents

## Pourquoi

- Distinguer visuellement les PRs ouvertes par les agents IA (Claude Code, Codex…) de celles ouvertes par un humain.
- Permettre à un humain d'**approuver** les PRs des agents (impossible si la PR est ouverte par soi-même avec branch protection "Require approvals").
- Préparer un modèle multi-agents : une App GitHub par agent, identité distincte sur chaque PR.

## Architecture

**Une GitHub App par agent**, installée sur tous les repos de l'org `kisnco`.

| Agent | App | Statut |
|---|---|---|
| Claude Code | `kisnco-claude-code` | ✅ actif (mai 2026) |
| Codex (futur) | `kisnco-codex` | ⏳ à créer |
| Autres agents | `kisnco-<nom>` | ⏳ à créer |

## App `kisnco-claude-code`

- **Owner** : `@kisnco`
- **App ID** : `3643047`
- **Client ID** : `Iv23liX7q2fuChtkm8NQ`
- **Installation ID** : `130539343`
- **Bot login** : `kisnco-claude-code[bot]` (auto-généré par GitHub)
- **Permissions repo** : Contents R+W · Pull requests R+W · Issues R+W · Workflows R+W · Metadata R
- **Webhooks** : désactivés (non nécessaires pour le use-case)
- **Repos accessibles** : `All repositories` de l'org `kisnco`

## Plomberie locale

### Secrets (hors repo)

```
~/.claude/secrets/
├── kisnco-claude-code.env              # APP_ID, INSTALLATION_ID, CLIENT_ID
└── kisnco-claude-code.private-key.pem  # clé privée RSA téléchargée depuis GitHub
```

Permissions : `chmod 700` sur le dossier, `chmod 600` sur les fichiers.

### Scripts (dans le repo)

| Script | Rôle |
|---|---|
| `scripts/gh-app-token.sh` | Génère un installation token (JWT signé → échangé contre token court ~1h) |
| `scripts/gh-app-bot.sh` | Wrapper unique : `push`, `pr-create`, `exec`, `token` |

Ces scripts sont **génériques** : changer `GH_APP_NAME` permet de basculer sur une autre App.

## Usage

### Pousser une branche en tant que bot

```bash
./scripts/gh-app-bot.sh push -u origin <branche>
```

Le wrapper convertit `git@github.com:kisnco/kisnlab.git` en `https://x-access-token:<token>@github.com/...` à la volée — sans toucher la config locale ni l'origin SSH (qui reste utilisable pour les push humains).

### Créer une PR en tant que bot

```bash
./scripts/gh-app-bot.sh pr-create --title "feat: ..." --body "..."
```

Le label `claude-generated` est ajouté automatiquement (convention projet).

### Exécuter une commande arbitraire avec le token

```bash
./scripts/gh-app-bot.sh exec gh pr list
./scripts/gh-app-bot.sh exec gh issue create --title "..."
```

`GITHUB_TOKEN` et `GH_TOKEN` sont exportés pour la commande.

### Debug

```bash
./scripts/gh-app-bot.sh token         # affiche le token brut (1h)
```

## Convention de commit/PR

- **Auteur des commits** : reste l'humain (Mélodie / collaborateur). Le bot ne change que **qui pousse** et **qui ouvre la PR**.
- **PR opener** : `kisnco-claude-code[bot]` → permet l'approbation par l'humain.
- **Label** : toute PR ouverte par le bot porte `claude-generated` (auto-ajouté par `pr-create`).

## Rotation de la clé privée

Si la clé est compromise :

1. GitHub → Settings de l'App → **Generate a new private key**
2. Remplacer `~/.claude/secrets/kisnco-claude-code.private-key.pem`
3. Révoquer l'ancienne clé sur la même page

L'`APP_ID` et `INSTALLATION_ID` ne changent pas.

## Ajouter un nouvel agent

1. Créer une nouvelle App `kisnco-<agent>` (mêmes permissions)
2. Installer sur "All repositories"
3. Télécharger le `.pem` → `~/.claude/secrets/kisnco-<agent>.private-key.pem`
4. Créer `~/.claude/secrets/kisnco-<agent>.env` (APP_ID + INSTALLATION_ID)
5. Utiliser : `GH_APP_NAME=kisnco-<agent> ./scripts/gh-app-bot.sh ...`
