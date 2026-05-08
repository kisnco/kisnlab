# GitHub Bot — Identité automation des agents

## Pourquoi

- Distinguer visuellement les PRs ouvertes par les agents IA (Claude Code, Codex…) de celles ouvertes par un humain.
- Permettre à un humain d'**approuver** les PRs des agents (impossible si la PR est ouverte par soi-même avec branch protection "Require approvals").
- Préparer un modèle multi-agents : une App GitHub par agent, identité distincte sur chaque PR.

## Architecture

**Une GitHub App par agent**, installée sur tous les repos de l'org `kisnco`.

| Agent | App | Statut |
|---|---|---|
| Claude Code (local) | `kisnlab-claude-code` | ✅ actif (2026-05-08) |
| Agent dev (LangGraph) | `kisnlab-dev` | ✅ actif (2026-05-08) — tools PR read+review câblés (`gh_pr_list/get/diff/review/comment`) |
| Codex (futur) | `kisnlab-codex` | ⏳ à créer |
| Autres agents | `kisnlab-<nom>` | ⏳ à créer |

## App `kisnlab-claude-code`

- **Owner** : `@kisnco`
- **App ID** : `3643047`
- **Client ID** : `Iv23liX7q2fuChtkm8NQ`
- **Installation ID** : `130539343`
- **Bot login** : `kisnlab-claude-code[bot]` (auto-généré par GitHub)
- **Permissions repo** : Contents R+W · Pull requests R+W · Issues R+W · Workflows R+W · Metadata R
- **Webhooks** : désactivés (non nécessaires pour le use-case)
- **Repos accessibles** : `All repositories` de l'org `kisnco`
- **Use-case** : PRs ouvertes par Claude Code en local depuis le terminal de Mélodie

## App `kisnlab-dev`

- **Owner** : `@kisnco`
- **App ID** : `3643429`
- **Client ID** : `Iv23liQzx8EgEVE4h2Sk`
- **Installation ID** : `130547284`
- **Bot login** : `kisnlab-dev[bot]` (auto-généré par GitHub)
- **Permissions repo** : Contents R+W · Pull requests R+W · Issues R+W · Workflows R+W · Metadata R
- **Webhooks** : désactivés
- **Repos accessibles** : `All repositories` de l'org `kisnco`
- **Use-case** : PRs et reviews automatisées par l'agent LangGraph `dev` (`services/api/app/agents/dev.py`). Inclut review entre agents : le bot dev peut review les PRs ouvertes par Claude Code et inversement.

### Tools côté agent (Python, `services/api/app/agents/tools/`)

| Module | Rôle |
|---|---|
| `github_app.py` | Charge les credentials, signe le JWT, échange contre installation token (cache 50 min, thread-safe) |
| `github_client.py` | Client HTTP : `list_prs`, `get_pr`, `get_pr_diff`, `review_pr`, `comment_pr` |
| `github_tools.py` | Wrappers `@tool` LangChain : `gh_pr_list`, `gh_pr_get`, `gh_pr_diff`, `gh_pr_review`, `gh_pr_comment` |

Scope volontairement réduit : **read + review uniquement** (pas de `git push` ni `gh_pr_create`). On les ajoutera quand un agent aura un déclencheur concret pour produire du code.

### Secrets dans le container `kisnlab-api`

Choix retenu : **(A) volume mount** dans `docker-compose.yml`.

```yaml
kisnlab-api:
  environment:
    GH_APP_NAME: kisnlab-dev
  volumes:
    - ${HOME}/.claude/secrets/kisnlab-dev.env:/secrets/kisnlab-dev.env:ro
    - ${HOME}/.claude/secrets/kisnlab-dev.private-key.pem:/secrets/kisnlab-dev.private-key.pem:ro
```

`github_app.load_credentials()` lit d'abord `/secrets/<app>.{env,private-key.pem}`. **Fallback** automatique sur les env vars `GH_APP_ID` / `GH_INSTALLATION_ID` / `GH_APP_PRIVATE_KEY` si les fichiers ne sont pas montés (utile pour le déploiement cloud à venir).

## Plomberie locale

### Secrets (hors repo)

```
~/.claude/secrets/
├── kisnlab-claude-code.env              # APP_ID, INSTALLATION_ID, CLIENT_ID
└── kisnlab-claude-code.private-key.pem  # clé privée RSA téléchargée depuis GitHub
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

Le wrapper override `remote.origin.url` en HTTPS le temps de la commande et injecte un credential helper inline avec le token — sans toucher la config locale ni l'origin SSH (qui reste utilisable pour les push humains). Tous les flags `git push` standards (`-u`, `-f`, `--tags`…) sont préservés.

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
- **PR opener** : `kisnlab-claude-code[bot]` → permet l'approbation par l'humain.
- **Label** : toute PR ouverte par le bot porte `claude-generated` (auto-ajouté par `pr-create`).

## Rotation de la clé privée

Si la clé est compromise :

1. GitHub → Settings de l'App → **Generate a new private key**
2. Remplacer `~/.claude/secrets/kisnlab-claude-code.private-key.pem`
3. Révoquer l'ancienne clé sur la même page

L'`APP_ID` et `INSTALLATION_ID` ne changent pas.

## Ajouter un nouvel agent

1. Créer une nouvelle App `kisnlab-<agent>` (mêmes permissions)
2. Installer sur "All repositories"
3. Télécharger le `.pem` → `~/.claude/secrets/kisnlab-<agent>.private-key.pem`
4. Créer `~/.claude/secrets/kisnlab-<agent>.env` (APP_ID + INSTALLATION_ID)
5. Utiliser : `GH_APP_NAME=kisnlab-<agent> ./scripts/gh-app-bot.sh ...`
