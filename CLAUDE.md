# KisnLab — Claude Code

## Qui je suis

**Développeuse senior & responsable technique — KIS'n Code**
Profil hybride : architecte technique · lead dev · accélératrice de projets

**Expertise principale**
- Symfony, API-first, Docker, CI/CD, sécurité (ISO 27001, SSO, auth)
- Refonte legacy · architecture scalable · pipelines CI/CD
- Vision produit + exécution technique

**Langages** : PHP/Symfony (fort) › JS/TS (fort) › Python (en apprentissage)
**Stack** : Symfony, React/Next.js, Tailwind, Docker, Postgres

**Philosophie** : _Keep It Simple, Make It Work_
→ Simplicité · Impact · Maîtrise — moins de complexité, plus de résultats.

---

## KIS'n Code

Boîte de développement & conseil.
**Clients** : TPE/PME, collectivités, porteurs de projets
**Offre** : dev sur mesure · refonte technique · archi propre · conseil structurant

---

## KisnLab

Stack IA auto-hébergée pour piloter KIS'n Code depuis Discord.
**Lire `docs/specs/` avant toute action.**

---

## Règles absolues

1. Lire le spec concerné dans `docs/specs/` avant de toucher à quoi que ce soit
2. Mettre à jour le spec + `CHANGELOG.md` après chaque modification significative
3. Ne jamais afficher ni lire `.env`
4. Ne jamais modifier `docker-compose.yml` ou `openclaw.json` sans montrer le diff d'abord
5. Toujours demander si c'est ambigu — une question vaut mieux qu'une erreur
6. Rester minimal : la solution la plus simple qui marche

---

## Ma méthode de travail

```
1. Lire le spec → comprendre le contexte
2. Proposer avant d'agir (si impact important)
3. Faire → minimal, fonctionnel, lisible
4. Mettre à jour le spec + CHANGELOG
```

**Priorités** : ça marche › ça ne casse rien › c'est lisible › c'est élégant

---

## Conventions

- Code en **anglais**, messages UI/Discord en **français**
- Indentation **2 espaces** partout
- Containers : préfixe `kisnlab-`
- Skills OpenClaw : frontmatter YAML + `approval: required` si envoi externe
- Workflows n8n : nommage `[pole]-[action]`

---

## docs/specs/ — La source de vérité

Mis à jour **à chaque modification** du composant concerné.

```
docs/specs/
├── STACK.md          → services Docker, ports, dépendances
├── DISCORD.md        → serveur, channels, bot, permissions
├── OPENCLAW.md       → config, skills, routing LLM, heartbeat
├── N8N.md            → workflows actifs, triggers, webhooks
├── DATABASE.md       → schéma Postgres, tables, pgvector
├── SKILLS.md         → liste des skills, rôles, LLM assigné
├── PROJETS.md        → projets actifs et leur état
└── CHANGELOG.md      → historique de toutes les modifications
```

---

## Commandes utiles

```bash
docker compose up -d
docker compose logs -f [service]
docker compose restart [service]
docker exec -it kisnlab-postgres psql -U kisnlab_admin
```
