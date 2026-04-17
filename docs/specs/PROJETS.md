# PROJETS.md — Projets actifs KIS'n Code

_Source de vérité pour les projets trackés par OpenClaw._
_Mettre à jour à chaque changement d'état significatif._

---

## Projets actifs (5)

### 1. Scoreboard Python — `scoreboard`

| | |
|--|--|
| **Type** | Client |
| **Stack** | Python, Node-RED |
| **État** | En cours |
| **Hébergement** | Local (Node-RED sur machine client) |
| **Contexte** | Tableau de bord de score avec simulation engine, progress bar, affichage temps réel |

**Prochaines actions** :
- Finaliser le debug de l'affichage après modification du scoreboard rush
- Valider le simulation engine Node-RED

---

### 2. Site KIS'n Code — `site`

| | |
|--|--|
| **Type** | Perso |
| **Stack** | À définir |
| **État** | Non démarré |
| **Hébergement** | Scaleway PLAY2-MICRO (existant) |
| **Contexte** | Site vitrine de l'activité freelance KIS'n Code |

**Prochaines actions** :
- Définir la stack (Symfony ? Next.js ?)
- Définir le contenu et l'arborescence

---

### 3. App Kis'n Way — `app-mobile`

| | |
|--|--|
| **Type** | Perso |
| **Stack** | React Native |
| **État** | En cours |
| **Hébergement** | Scaleway PLAY2-MICRO (existant) |
| **Contexte** | Application d'alignement / bien-être. Backend sur Scaleway. |

> ⚠️ Le PLAY2-MICRO est dédié à Kis'n Way + site KIS'n Code. Ne pas y déployer KisnLab.

**Prochaines actions** :
- À préciser

---

### 4. Nouvelle prestation IA — `prestation`

| | |
|--|--|
| **Type** | Perso |
| **Stack** | À définir |
| **État** | Idéation |
| **Hébergement** | À définir |
| **Contexte** | Offre de prestation autour de l'IA agentique — à structurer et positionner |

**Prochaines actions** :
- Définir l'offre avec `strategie-conseiller`
- Rédiger une proposition de valeur

---

### 5. Outil comptabilité SASU — `comptabilite`

| | |
|--|--|
| **Type** | Perso |
| **Stack** | À définir |
| **État** | Non démarré |
| **Hébergement** | À définir |
| **Contexte** | Outil interne pour simplifier le suivi comptable de la SASU |

**Prochaines actions** :
- Définir le périmètre (remplace-t-il Pennylane/Freebe ou s'y connecte ?)
- Estimation de la charge

---

## Infrastructure partagée

| Ressource | Assignation |
|-----------|------------|
| MacBook Pro Intel 2019 (32 Go) | Dev local + KisnLab V1 |
| Scaleway PLAY2-MICRO | Kis'n Way + Site KIS'n Code **uniquement** |
| Mac mini M4 Pro 48 Go _(juin 2026)_ | KisnLab V2 production 24/7 |
