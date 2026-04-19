# 📊 GitHub Dashboard — Setup & Deployment

**Status:** ✅ Ready to Deploy  
**Date:** 2026-04-19  

---

## 🎯 Qu'est-ce que c'est?

Un **dashboard GitHub interactif dans Discord** qui affiche :
- 📊 Status général (repos, commits, health)
- 🔀 Branches actives + commits récents
- 🐛 Issues & PRs ouvertes
- ✅ CI/CD status (lint, healthcheck, pr-checks)
- 🚀 Quick actions (commandes recommandées)

**Utilisation :**
```
@bot dashboard
→ Embed rafraîchissable avec 6 vues via reactions
```

---

## 📦 Fichiers Créés

| Fichier | Rôle |
|---------|------|
| `skills/github-dashboard/SKILL.md` | Documentation complète |
| `/home/node/.openclaw/workspace/skills/github-dashboard/scripts/dashboard.py` | Générateur d'embeds |

---

## 🚀 Activation (3 étapes)

### Étape 1 : Vérifier Prérequis

```bash
# Token présent
grep GITHUB_TOKEN .env | head -1
# Output: GITHUB_TOKEN=github_pat_...

# Discord channel configuré
grep DISCORD_CHANNEL_DEV .env | head -1
# Output: DISCORD_CHANNEL_DEV=1495504483298447411

# Python disponible
python3 --version
# Output: Python 3.10+
```

### Étape 2 : Enregistrer le Skill

Ajouter dans `config/openclaw/openclaw.json` (section `skills`) :

```json
{
  "skills": [
    ...
    {
      "name": "github-dashboard",
      "enabled": true,
      "description": "Discord GitHub dashboard avec embeds interactifs",
      "triggers": ["dashboard"]
    }
  ]
}
```

Ou via CLI :
```bash
openclaw config add skills github-dashboard
```

### Étape 3 : Redémarrer OpenClaw

```bash
docker compose restart openclaw
```

---

## ✅ Test

### Test 1 : Commande Discord

Dans `#dev` channel :
```
@KisnLab Bot dashboard
```

**Résultat attendu :**
```
[Embed avec titre "🚀 KisnLab — GitHub Status"]
[Affiche : repo, branch, last commit, status, health]
[Reactions: 📊 🔀 🐛 ✅ 🚀 🔄]
```

### Test 2 : Interactions

Cliquer sur réactions :
- 📊 → Affiche statistiques détaillées
- 🔀 → Affiche branches + commits
- 🐛 → Affiche issues & PRs
- ✅ → Affiche CI/CD status
- 🚀 → Affiche quick actions
- 🔄 → Refresh l'embed principal

### Test 3 : Commande depuis dashboard

Cliquer sur 🚀, puis dans Discord :
```
@bot crée une issue : "Test depuis dashboard"
```

**Résultat :** Issue créée, dashboard se met à jour après quelques secondes.

---

## 🔄 Auto-Refresh (Optional)

Pour mettre à jour le dashboard automatiquement :

### Option A : Webhook GitHub

**1. Créer webhook GitHub**

```bash
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/kisnco/kisnlab/hooks \
  -d '{
    "name": "web",
    "active": true,
    "events": ["push", "pull_request"],
    "config": {
      "url": "https://openclaw.kisnlab.local/plugins/webhooks/github",
      "content_type": "json",
      "secret": "'$OPENCLAW_WEBHOOK_SECRET'"
    }
  }'
```

**2. Dashboard se met à jour après chaque push/PR** ✅

### Option B : Cron Job (Simple)

```bash
# Ajouter dans openclaw.json
{
  "cron": {
    "dashboard-refresh": {
      "schedule": "*/30 * * * *",  // Toutes les 30min
      "task": "github-dashboard",
      "action": "refresh"
    }
  }
}
```

### Option C : Manual (Toujours dispo)

```
@bot dashboard refresh
```

---

## 📊 Exemple d'Embed

```
🚀 KisnLab — GitHub Status

📊 Repository
kisnlab
Branch: dev
Last: 163aa56 - docs: résumé complet

📈 Status
CI/CD: ✅ All pass
Issues: 2 open
PRs: 0 open
Health: ✅ Excellent

🔧 Quick Actions
React: 📊 stats | 🔀 branches | 🐛 issues | ✅ CI/CD | 🚀 actions | 🔄 refresh

---
Last updated: 2026-04-19 20:39:15 UTC
```

---

## 🔐 Sécurité

✅ Pas de secrets dans les embeds  
✅ GITHUB_TOKEN utilisé que en API calls (jamais envoyé Discord)  
✅ Données publiques seulement (repos, issues, branches)  
✅ Channel #dev accessible seulement à `kisnco`  

---

## 🎯 Cas d'Usage

### Avant Travail
```
@bot dashboard
→ Voir si tout est ✅ avant de commencer
```

### Après Push
```
Dashboard se met à jour auto (webhook ou cron)
→ Voir CI/CD status en temps réel
```

### Créer Feature
```
@bot dashboard
→ React 🚀
→ @bot nouvelle branche feat/ma-feature
→ Dashboard met à jour
```

### Merger PR
```
@bot merge la PR #42
→ Dashboard auto-refresh
→ Voir que PR est merged, branch supprimée
```

---

## 📈 Prochaines Améliorations

- [ ] Alertes si checks failent
- [ ] Graphique commits/semaine (sparklines)
- [ ] Diff view (main vs dev)
- [ ] Boutons cliquables (si Discord le permet)
- [ ] Intégration n8n workflows status
- [ ] Multi-repo dashboard

---

## ❓ FAQ

**Q: Où le dashboard est-il affiché ?**  
A: Dans le channel `#dev`. Peut être customisé dans openclaw.json.

**Q: Comment il se met à jour ?**  
A: Webhook GitHub (après push/PR) ou cron (30min) ou manual (`@bot dashboard refresh`).

**Q: Les reactions marchent sur mobile ?**  
A: Oui ! Discord API supporte les reactions sur tous les devices.

**Q: Peut-on avoir plusieurs dashboards (par repo) ?**  
A: Oui ! Créer des instances différentes avec des triggersDifferents.

---

## 🔧 Support

**Problème ?**

1. Vérifier logs :
   ```bash
   docker compose logs openclaw | grep dashboard
   ```

2. Check token :
   ```bash
   grep GITHUB_TOKEN .env | wc -c
   # Output: doit être > 50 chars
   ```

3. Check channel :
   ```bash
   grep DISCORD_CHANNEL_DEV .env
   ```

4. Relancer :
   ```bash
   docker compose restart openclaw
   ```

---

**Ready ! Lance `@bot dashboard` 🚀**
