# Comparaison : `dev-project-manager` vs `github-manager`

## 📊 Vue d'ensemble

| Aspect | dev-project-manager | github-manager |
|--------|---------------------|----------------|
| **Scope** | KIS'n Code + KisnLab stack | Général, tous repos |
| **Focus** | Gestion de projet intégrée | Pure GitHub ops |
| **Accès** | GitHub + Docker + File system | GitHub API seulement |
| **Channel** | `#dev` (Discord) | Transversal |
| **LLM** | `primary` (Sonnet) | Par défaut (Haiku) |
| **Approval** | ✅ Required | ❌ Non-requis |

---

## 🎯 Fonctionnalités par Skill

### `dev-project-manager` (Existant dans kisnlab)

**Unique :**
- ✅ Pilote stack KisnLab (Docker, containers)
- ✅ Accès filesystem repo `/repo/kisnlab`
- ✅ Intégration Discord `#dev` channel
- ✅ Approval workflow obligatoire
- ✅ Commandes Discord high-level ("liste mes projets", "redémarre [service]")

**Limitations :**
- ❌ Pas de script réutilisable (référence manuelle à curl)
- ❌ Docker API via curl unix socket (basique)
- ❌ Pas d'exemple de code pour les opérations complexes

### `github-manager` (Nouveau, générique)

**Unique :**
- ✅ Script Python réutilisable (`github_ops.py`)
- ✅ Patterns complets pour toutes les opérations GitHub
- ✅ Workflows avancés (PR merge, review, etc.)
- ✅ Pas de dépendance Docker
- ✅ Générique → fonctionne avec n'importe quel repo

**Limitations :**
- ❌ Pas d'intégration Discord native
- ❌ Pas de contrôle Docker
- ❌ Pas d'accès filesystem external

---

## 🤝 Comment les Utiliser Ensemble

### Scénario 1 : "Crée une feature sur KisnLab"
→ **Use `dev-project-manager`**
```
@bot crée une branche feat/github-integration sur kisnlab
→ Fait la branche, valide, affiche confirmation #dev
```

### Scénario 2 : "Crée une issue sur n'importe quel repo"
→ **Use `github-manager`**
```
@bot crée une issue : "Fix bug X"
→ Plus flexible, n'importe quel repo
```

### Scénario 3 : "Review du code + redémarre n8n après merge"
→ **Use `dev-project-manager` (orchestration)**
```
@bot review la PR #42 et redémarre n8n
→ Combine GitHub + Docker
```

---

## 💡 Recommandations

### ✅ Garder `dev-project-manager`
- C'est le **gestionnaire de KisnLab** → spécifique au projet
- Interaction Discord, approval workflow
- Pilote l'infrastructure (Docker)

### ✅ Ajouter `github-manager`
- **Transversal** pour tous les repos
- Workflows réutilisables
- Plus léger pour opérations GitHub simples

### 🔗 Intégration proposée
```
dev-project-manager
  ├── Routes GitHub vers github-manager (pour opérations pures)
  ├── Gère Docker + KisnLab spécifique
  └── Orchestration métier
```

---

## 🚀 Plan de Fusion

### Phase 1 (Court terme)
- [ ] Améliorer `dev-project-manager` avec script Python similaire à `github-manager`
- [ ] Ajouter exemples de code pour curl unix socket Docker
- [ ] Tester commandes Discord existantes

### Phase 2 (Moyen terme)
- [ ] Créer `github-manager` en tant que skill transversal
- [ ] Références croisées entre les deux skills
- [ ] Ajouter webhook Discord depuis `github-manager` (announcements)

### Phase 3 (Long terme)
- [ ] Dashboard GitHub centralisé
- [ ] Monitoring repos en temps réel
- [ ] Automation workflows basée sur événements GitHub

---

## 📝 Code Proposals

### Pour `dev-project-manager` : Améliorer Docker API
```bash
# Lister containers (meilleur que curl unix socket)
TOKEN=$(grep "^GITHUB_TOKEN=" /repo/kisnlab/.env | cut -d= -f2)

# Vérifier si service est up
docker compose -f /repo/kisnlab/docker-compose.yml ps

# Logs en temps réel
docker compose -f /repo/kisnlab/docker-compose.yml logs -f [service]
```

### Pour `github-manager` : Discord Webhook announcements
```python
# Envoyer notifications dans Discord après créer une issue
import json
webhook_url = os.getenv('DISCORD_WEBHOOK_DEV')
payload = {
    "content": f"✅ Issue créée: {issue_url}",
    "embeds": [...]
}
requests.post(webhook_url, json=payload)
```

---

## ✨ Verdict

**`dev-project-manager` et `github-manager` sont complémentaires, pas concurrents.**

- **Garde `dev-project-manager`** → gestionnaire intégré KisnLab
- **Ajoute `github-manager`** → opérations GitHub génériques
- **Relie les deux** via webhooks Discord + appels croisés

Chaque skill a son rôle, ensemble ils forment un système cohérent. 🎯
