---
name: github-dashboard
description: Discord GitHub dashboard — affiche status repos, branches, issues, PRs, CI/CD avec embeds rafraîchissables. Use when: (1) `dashboard` command from Discord, (2) scheduled status checks, or (3) real-time updates after push/PR. Posts rich embeds with reactions for filtering. Requires GITHUB_TOKEN and Discord channel access.
---

# GitHub Dashboard

Affiche un **dashboard GitHub interactif** dans Discord avec status en temps réel.

## Utilisation

### Commande Discord

```
@bot dashboard
```

→ Envoie un embed avec :
- ✅ Status général (health check)
- 📊 Statistiques repos
- 🔀 Branches actives
- 🐛 Issues ouvertes
- ✅ CI/CD status
- 🚀 Prochaines actions

### Réactions Interactives

Une fois l'embed posté, utilise les réactions pour filtrer :

| Réaction | Affiche |
|----------|---------|
| 📊 | Statistiques détaillées (commits, size, contributors) |
| 🔀 | Branches + derniers commits |
| 🐛 | Issues et PRs ouvertes |
| ✅ | CI/CD status (derniers runs) |
| 🚀 | Actions rapides (create issue, branch, etc.) |
| 🔄 | Rafraîchir le dashboard |

---

## 📊 Contenu de l'Embed

### Vue Principale

```
🚀 KisnLab — GitHub Status

📊 Repo: kisnlab
Branch: dev (8 commits ahead de main)
Last commit: 163aa56 - docs: résumé complet [2min ago]

📈 Status
├─ CI/CD: ✅ All checks pass
├─ Issues: 2 open
├─ PRs: 0 open
└─ Health: ✅ Excellent

🔧 React 📊 📊 🐛 ✅ 🚀 pour plus de détails
```

### Vue Statistiques (📊 réaction)

```
📈 Statistiques Détaillées

kisnlab
├─ Commits: 8 (cette semaine: 7)
├─ Contributors: 1
├─ Size: 1.1 MB
├─ Branches: 2 (main, dev)
├─ Issues: 2 open, 0 closed
├─ PRs: 0 open, 0 closed
└─ Releases: 0 (suggestion: v0.1.0)
```

### Vue Branches (🔀 réaction)

```
🔀 Branches Actives

main (origin/main)
└─ Last: 3b688f1 - docs: mise à jour README [2 jours ago]
   Status: ✅ All checks pass

dev (origin/dev) ← CURRENT
└─ Last: 163aa56 - docs: résumé complet [2min ago]
   Status: ✅ All checks pass
   Ahead: 8 commits de main
```

### Vue Issues (🐛 réaction)

```
🐛 Issues & PRs

ISSUES (2 open)
├─ #1 [BUG] Pas de versioning/releases (créée il y a 1h)
└─ #2 [FEAT] Ajouter webhook Discord notifications (créée il y a 30min)

PRs (0 open)
└─ Aucune PR en attente
```

### Vue CI/CD (✅ réaction)

```
✅ CI/CD Status

Derniers Runs (cette semaine)
├─ lint.yml ✅ [dev, 5min ago]
│  └─ Shell ✅ | Docker ✅ | JSON ✅ | Skills ✅ | Env ✅
├─ healthcheck.yml ✅ [scheduled, 12h ago]
│  └─ Secrets ✅ | Stats ✅ | Health ✅
└─ pr-checks.yml ⏳ [pending next PR]
   └─ Will check: metadata, branch naming, commits

Success Rate: 100% (2/2 checks passed)
```

### Vue Actions (🚀 réaction)

```
🚀 Quick Actions

@bot crée une issue : "titre"
@bot nouvelle branche feat/nom
@bot merge la PR #123
@bot crée release v1.0.0
@bot git status
@bot docker-ps

↳ Ou tape directement dans #dev !
```

---

## ⚙️ Implémentation

### 1. Données Source

L'embed utilise ces sources :

**GitHub API :**
- `GET /user/repos` → liste repos
- `GET /repos/{owner}/{repo}` → détails repo
- `GET /repos/{owner}/{repo}/issues` → issues
- `GET /repos/{owner}/{repo}/pulls` → PRs
- Actions API → CI/CD status

**Local Git :**
- `git log --oneline` → commits récents
- `git branch -a` → branches
- `git status` → uncommitted changes

**Docker :**
- `docker compose ps` → service health

### 2. Refresh Logic

Dashboard se rafraîchit :

**Automatiquement :**
- Toutes les 30min (cron job)
- Après chaque push (webhook GitHub)
- Après chaque PR (webhook GitHub)

**Manuellement :**
- Réaction 🔄 sur l'embed
- Commande `@bot dashboard refresh`

### 3. Stockage du Message

L'embed ID est stocké pour édition :

```json
{
  "dashboard_message_id": "1495524380363587788",
  "dashboard_channel_id": "1495504483298447411",
  "last_refresh": "2026-04-19T20:39:00Z",
  "repo": "kisnco/kisnlab"
}
```

---

## 🔗 Intégration avec Autres Skills

**Compatible avec :**
- `dev-project-manager` — Orchestre actions (branch, issue, merge)
- `github-manager` — Opérations GitHub pures
- n8n webhooks — Déclenche updates automatiques

**Workflow :**
```
GitHub Event (push/PR)
  ↓
n8n Webhook
  ↓
Discord Webhook
  ↓
github-dashboard skill (met à jour embed)
  ↓
User voir status mis à jour en temps réel
```

---

## 📝 Exemples d'Utilisation

### Cas 1 : Vérifier la santé du repo avant travail

```
@bot dashboard
→ Embed s'affiche avec ✅ tout bon
→ J'ouvre le code, je lance ma feature
```

### Cas 2 : Merger une PR et voir l'impact

```
@bot merge la PR #42
→ PR merges
→ GitHub Actions tourne
→ Dashboard se met à jour automatiquement
→ Voir status CI/CD en temps réel
```

### Cas 3 : Checker issues en attente

```
@bot dashboard
→ React avec 🐛
→ Voir les 2 issues ouvertes
→ Cliquer sur liens GitHub pour détails
```

### Cas 4 : Créer release depuis le dashboard

```
@bot dashboard
→ React avec 🚀
→ Voir "v0.1.0 prêt à être créé"
→ @bot crée release v0.1.0
→ Dashboard se met à jour (0 releases → 1 release)
```

---

## 🎯 Prochaines Améliorations

- [ ] Ajouter webhook GitHub pour auto-update
- [ ] Ajouter boutons cliquables (si Discord supporte)
- [ ] Afficher diff entre main et dev
- [ ] Graphique commits par semaine
- [ ] Alertes si checks failent
- [ ] Intégration avec n8n (afficher workflow status)

---

## 🛠️ Code & Scripts

Voir `scripts/dashboard.py` pour l'implémentation complète.

---

**Prêt ? Lance : `@bot dashboard` ! 🚀**
