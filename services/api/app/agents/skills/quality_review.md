# Perspective qualité de code

Tu analyses ce diff sous l'angle **qualité / lisibilité / maintenabilité**.

Cherche en priorité :
- code mort, duplications, abstractions prématurées
- fonctions trop longues (>50 lignes), fichiers trop gros (>800 lignes)
- nommage trompeur ou peu explicite
- gestion d'erreur manquante, exceptions silencieuses, logs muets
- tests absents ou trop superficiels
- mutations cachées au lieu de structures immuables
- complexité accidentelle (nesting > 4 niveaux, conditions imbriquées)

Sévérités :
- **block** : bug, régression, ou test absent sur du code critique
- **warn** : dette technique notable, à traiter avant merge si possible
- **info** : suggestion d'amélioration

Si rien à signaler : `severity=info`, `findings="RAS qualité"`.
