# Migration sécurité OpenClaw — Étapes à exécuter

> Plan complet : `/Users/melo/.claude/plans/floofy-tickling-sky.md`
> CHANGELOG : `docs/specs/CHANGELOG.md` § 2026-04-25

Cette doc guide la **mise en route** des changements après que toute la phase de code (Dockerfile, docker-compose, skill, templates, specs) soit committée.

---

## Étape 1 — Récupérer un GitHub token sécurisé

1. Va sur https://github.com/settings/personal-access-tokens
2. **Generate new token** → **Fine-grained**
3. Configure :
   - **Token name** : `kisnlab-openclaw`
   - **Expiration** : 90 jours (mets-toi un rappel calendrier pour rotater)
   - **Resource owner** : `kisnco`
   - **Repository access** : Selected repositories → `kisnlab` + tout autre repo que OpenClaw doit gérer (scoreboard, site, app-mobile, etc.)
   - **Permissions repository** :
     - Contents : **Read and write**
     - Pull requests : **Read and write**
     - Issues : **Read and write**
     - Workflows : **Read-only** ⚠️ (jamais write — sinon l'agent peut éditer la CI)
     - Metadata : Read-only (auto)
     - **PAS** d'accès Secrets, Actions secrets, Administration
4. Copie le token `ghp_...` ou `github_pat_...`
5. Mets-le dans `.env` :
   ```bash
   GITHUB_TOKEN=github_pat_<ton-token>
   ```

---

## Étape 2 — Authentifier `gh` localement (pour la branch protection)

```bash
gh auth login
# Choisis : GitHub.com → HTTPS → Login with a web browser
# Suis le flow d'auth, c'est rapide
gh auth status   # vérifie que c'est OK
```

---

## Étape 3 — Compléter CODEOWNERS

```bash
# Récupère ton handle GitHub
gh api user --jq .login
# Disons que ça affiche : melodie-onestas
```

Édite `.github/CODEOWNERS` et remplace `@REPLACE-WITH-YOUR-GITHUB-USERNAME` par `@<ton-handle>` (avec le `@`, sans `https://...`).

---

## Étape 4 — Activer la branch protection

```bash
cd /Users/melo/ProjetsDev/kisnlab
bash scripts/setup-branch-protection.sh
```

Le script :
- Vérifie que tu es authentifié et admin sur `kisnco/kisnlab`
- Active la protection sur `main` et `dev` :
  - PR obligatoire (1 review minimum, CODEOWNERS exigé)
  - Status checks verts (`pr-checks`, `lint`, `healthcheck`)
  - Pas de force push, pas de suppression de branche

Pour vérifier après coup :
```bash
gh api repos/kisnco/kisnlab/branches/dev/protection --jq .
gh api repos/kisnco/kisnlab/branches/main/protection --jq .
```

---

## Étape 5 — Builder l'image custom et démarrer la stack

```bash
cd /Users/melo/ProjetsDev/kisnlab

# Vérifie qu'on n'a rien oublié
bash scripts/preflight.sh

# Stop ce qui tourne (au cas où)
docker compose down

# Build l'image custom (~2-3 min : pull base + apt install docker-cli + gh)
docker compose build openclaw

# Up complet (DinD démarre en premier grâce au depends_on)
docker compose up -d

# Suit les logs des deux services pendant 30s
docker compose logs -f openclaw openclaw-dind &
sleep 30 && kill %1 2>/dev/null
```

---

## Étape 6 — Vérifications end-to-end

### Tests d'isolation Docker

```bash
# DinD healthy
docker compose ps openclaw-dind | grep -q healthy && echo OK

# OpenClaw voit la DinD, pas le host
docker exec kisnlab-openclaw docker version
#   Server Version doit être Docker Engine 26.x (DinD), pas la version de Docker Desktop

# Le socket host n'est PLUS monté
docker exec kisnlab-openclaw ls /var/run/docker.sock 2>&1
#   doit afficher : No such file or directory

# Tentative d'escape vers le host (test négatif — doit échouer)
docker exec kisnlab-openclaw docker run --rm --privileged alpine ls /host
#   ne doit voir QUE le FS de la DinD, pas /Users, pas /etc du Mac
```

### Tests d'isolation repo

```bash
# Repo en read-only
docker exec kisnlab-openclaw touch /repo/kisnlab/test-write 2>&1
#   doit afficher : Read-only file system

# Workspace en read-write
docker exec kisnlab-openclaw touch /workspace/work/test-write && \
  docker exec kisnlab-openclaw rm /workspace/work/test-write && \
  echo "workspace OK"
```

### Tests CLI

```bash
docker exec kisnlab-openclaw docker --version
docker exec kisnlab-openclaw gh --version
docker exec kisnlab-openclaw gh auth status
#   doit afficher : Logged in to github.com account ... (via GH_TOKEN)
docker exec kisnlab-openclaw gh repo list kisnco --limit 5
```

### Test end-to-end GitOps (depuis Discord)

Demande à OpenClaw dans le channel `#dev` :

> "Sur kisnlab, ajoute un commentaire en haut de README.md disant 'managed by OpenClaw'"

Attendu :
1. Il clone `kisnco/kisnlab` dans `/workspace/work/kisnlab`
2. Crée la branche `feature/openclaw-readme-comment` (ou similaire)
3. Modifie le fichier
4. Commit + push
5. Ouvre une PR draft sur `dev` avec le label `openclaw-generated`
6. La PR apparaît sur GitHub : https://github.com/kisnco/kisnlab/pulls
7. Les workflows CI tournent (pr-checks, lint, healthcheck)
8. **Tu dois reviewer et approuver** la PR avant qu'elle puisse être mergée

### Test négatif — push direct interdit

```bash
docker exec kisnlab-openclaw bash -c '
  cd /tmp && gh repo clone kisnco/kisnlab kisnlab-test 2>/dev/null
  cd kisnlab-test && git checkout dev
  echo "test direct push" >> README.md
  git -c user.email=openclaw@kisnlab.local -c user.name=openclaw commit -am "test"
  git push origin dev 2>&1
'
#   Doit afficher : "protected branch hook declined" ou similaire
```

---

## Étape 7 — Surveillance continue

### À mettre en place plus tard (hors scope de cette migration)

- **Alertes Langfuse** : coût > seuil, nombre de tool calls anormal
- **Cron de purge DinD** : `docker exec kisnlab-openclaw-dind docker system prune -af` hebdo (n8n workflow)
- **Veille CVE Docker** : vu que la DinD est privileged, surveiller les CVEs runtime
- **Rotation `GITHUB_TOKEN`** : tous les 90 jours

---

## Rollback (en cas de problème)

```bash
docker compose down
git revert <commit-de-la-migration>
docker compose up -d
```

Ou pour récupérer juste l'ancienne config sans rollback git :
- Remettre `image: alpine/openclaw:latest` à la place du `build:`
- Remettre `/var/run/docker.sock:/var/run/docker.sock` (pas recommandé !)
- Remettre `.:/repo/kisnlab` (sans `:ro`)

⚠️ Le rollback ramène la faille de sécu — uniquement en dernier recours.

---

## Hors scope de cette migration (à traiter ensuite)

Voir `docs/specs/CHANGELOG.md` § 2026-04-25 "Hors scope" :

1. Rotation de la clé Anthropic en clair dans `config/openclaw/agents/main/auth-profiles.json`
2. Restriction du tool profile `"coding"` → allowlist stricte
3. `read_only: true` + `user:` override sur openclaw
4. Egress proxy avec allowlist domaines (api.anthropic.com, api.github.com, ...)
5. Hardening du system prompt OpenClaw contre prompt injection
