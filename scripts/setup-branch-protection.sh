#!/usr/bin/env bash
# =============================================================================
# setup-branch-protection.sh — Configure la branch protection sur main + dev
# =============================================================================
# Doc API : https://docs.github.com/en/rest/branches/branch-protection
#
# À exécuter UNE FOIS, manuellement, après :
# 1. `gh auth login` (avec un compte qui a les droits admin sur kisnco/kisnlab)
# 2. CODEOWNERS rempli avec ton vrai username GitHub
#
# Effet :
# - Toute PR doit être approuvée par 1 reviewer (et CODEOWNERS si applicable)
# - Les status checks pr-checks/lint/healthcheck doivent être verts
# - Force push interdit
# - Suppression de branche interdite
# =============================================================================

set -euo pipefail

REPO="${REPO:-kisnco/kisnlab}"

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI introuvable. Installe-la : https://cli.github.com" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: pas authentifié. Lance 'gh auth login' d'abord." >&2
  exit 1
fi

# Vérifier les permissions admin sur le repo
if ! gh api "repos/${REPO}" --jq '.permissions.admin' 2>/dev/null | grep -q true; then
  echo "ERROR: tu n'as pas les droits admin sur ${REPO}." >&2
  exit 1
fi

protect_branch() {
  local branch="$1"
  echo "→ Protection de la branche '${branch}' sur ${REPO}..."

  # Source des champs : https://docs.github.com/en/rest/branches/branch-protection
  gh api -X PUT "repos/${REPO}/branches/${branch}/protection" \
    --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["pr-checks", "lint", "healthcheck"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": false
}
EOF

  echo "✓ ${branch} protégée"
}

# Vérifier que les branches existent avant de tenter de les protéger
for branch in main dev; do
  if gh api "repos/${REPO}/branches/${branch}" --silent >/dev/null 2>&1; then
    protect_branch "${branch}"
  else
    echo "⚠️  Branche '${branch}' inexistante sur ${REPO} — skip"
  fi
done

echo
echo "Récap :"
gh api "repos/${REPO}/branches" --jq '.[] | select(.protected == true) | .name' \
  | sed 's/^/  ✓ /'

echo
echo "Note : pour vérifier en détail une protection :"
echo "  gh api repos/${REPO}/branches/dev/protection --jq ."
