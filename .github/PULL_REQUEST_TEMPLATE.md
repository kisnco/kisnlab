<!--
Si la PR est ouverte par OpenClaw, vérifier que le label `openclaw-generated`
est appliqué automatiquement. Pour les humains, supprimer ce commentaire.
-->

## Quoi

<!-- Une phrase claire : qu'est-ce qui change ? -->

## Pourquoi

<!-- Le contexte : pourquoi c'est nécessaire ? Quel problème ça résout ?
Lien vers issue, spec, ou conversation Discord si pertinent. -->

## Comment tester

<!--
Étapes concrètes pour vérifier que ça marche :
- [ ] Étape 1
- [ ] Étape 2
- [ ] Vérifier que les checks CI passent (lint, healthcheck, pr-checks)
-->

## Sécurité

<!--
Cocher uniquement ce qui s'applique. Si une case sensible est cochée,
expliquer brièvement comment c'est mitigé.
-->

- [ ] Aucun secret commité (vérifier `.env`, clés API, tokens)
- [ ] Pas de modification de `docker-compose.yml`, `Dockerfile.openclaw` ou `.github/`
- [ ] Pas de nouvelle dépendance externe (sinon : justification + audit)
- [ ] Pas de nouvelle surface d'attaque (endpoint, webhook, port exposé)
- [ ] Pas de nouvelle permission demandée (capabilities Docker, scopes GitHub, etc.)

## Checklist

- [ ] Documentation à jour (`docs/specs/` si touche au stack/skills/DB)
- [ ] `CHANGELOG.md` mis à jour si modification significative
- [ ] Tests ajoutés ou mis à jour si applicable
- [ ] Convention de commit respectée (`feat:`, `fix:`, etc.)
- [ ] Branche au format attendu (`feature/`, `fix/`, `docs/`, etc.)

---

<!-- Notes additionnelles, captures d'écran, liens... -->
