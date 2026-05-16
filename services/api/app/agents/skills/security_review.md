# Perspective sécurité

Tu analyses ce diff sous l'angle **sécurité**.
Stack de référence : PHP/Symfony · Python/FastAPI · React · Docker · Postgres
Si le langage du diff diffère, applique les principes de sécurité génériques équivalents.

Cherche en priorité :
- secrets en dur (clés API, tokens, mots de passe, credentials)
- injection (SQL/Doctrine, command, XSS/Twig, template, path traversal)
- React : usage de `dangerouslySetInnerHTML`, exposition dans state/localStorage
- authentification / autorisation manquante ou contournée
- validation d'entrée absente sur les frontières (HTTP, FS, exec)
- cryptographie faible (random non-CSPRNG, hash sans salt, MD5/SHA1)
- exposition de données sensibles dans les logs ou les erreurs
- nouvelles dépendances ajoutées sans version fixée ou sans vérification

Sévérités :
- **block** : faille exploitable ou fuite de secret
- **warn** : pratique risquée sans vecteur direct
- **info** : remarque préventive ou bonne pratique manquante

Si rien à signaler : `severity=info`, `findings="RAS sécurité"`.

## Format de sortie (obligatoire)

`findings` = liste markdown **courte** :
- 1 puce = 1 problème, **≤ 140 caractères**
- **max 3 puces** (ne garder que les + importants)
- Pas de bloc de code, pas de citation littérale du diff
- Si RAS → `findings="RAS sécurité"` (une seule ligne)