# Outils GitHub PR

- `gh_pr_list(repo, state)` : lister les PRs.
- `gh_pr_get(repo, number)` : metadata d'une PR.
- `gh_pr_diff(repo, number)` : diff unifié.
- `gh_pr_review(repo, number, event, body)` : APPROVE / REQUEST_CHANGES / COMMENT.
- `gh_pr_comment(repo, number, body)` : simple commentaire.

Pour reviewer : lis d'abord le diff (`gh_pr_diff`), puis poste une review structurée.
Approuve seulement si tu n'as pas de remarque bloquante.
