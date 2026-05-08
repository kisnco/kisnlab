#!/usr/bin/env bash
# Wrapper pour exécuter git/gh avec l'identité du bot GitHub App.
#
# Usage:
#   ./scripts/gh-app-bot.sh push [args]            # git push avec token bot (HTTPS+token sur la volée)
#   ./scripts/gh-app-bot.sh pr-create [args]       # gh pr create + label claude-generated
#   ./scripts/gh-app-bot.sh exec <cmd> [args]      # exécute une commande quelconque avec GITHUB_TOKEN/GH_TOKEN exporté
#   ./scripts/gh-app-bot.sh token                  # affiche juste le token
#
# Variable d'environnement :
#   GH_APP_NAME — sélectionne l'App (défaut : kisnco-claude-code)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="${GH_APP_NAME:-kisnco-claude-code}"

usage() {
  cat <<EOF
Usage:
  $0 push [git-push-args]            Push branche courante avec l'identité du bot
  $0 pr-create [gh-pr-create-args]   Crée une PR (auto-ajoute le label 'claude-generated')
  $0 exec <command> [args...]        Exécute <command> avec GITHUB_TOKEN/GH_TOKEN exporté
  $0 token                           Affiche le token (debug)

Variable d'env:
  GH_APP_NAME  — sélectionne l'App (défaut: $APP_NAME)
EOF
}

if [[ $# -eq 0 ]]; then
  usage >&2
  exit 1
fi

# Récupère le token (court-vivant, ~1h)
TOKEN=$("${SCRIPT_DIR}/gh-app-token.sh" "$APP_NAME")
export GITHUB_TOKEN="$TOKEN"
export GH_TOKEN="$TOKEN"

# Convertit l'URL origin SSH → HTTPS (sans token dans l'URL — auth via credential helper)
origin_as_https() {
  local remote_url
  remote_url=$(git config --get remote.origin.url)
  if [[ "$remote_url" =~ ^git@github\.com:(.+)$ ]]; then
    echo "https://github.com/${BASH_REMATCH[1]}"
  elif [[ "$remote_url" =~ ^https://(.*@)?(github\.com/.+)$ ]]; then
    echo "https://${BASH_REMATCH[2]}"
  else
    echo "Erreur : remote.origin.url non géré : $remote_url" >&2
    return 1
  fi
}

# Lance git avec : (a) origin override en HTTPS, (b) credential helper inline avec le token.
# Préserve tous les flags standards (-u, -f, etc.) car on push sur le nom 'origin'.
git_with_bot_creds() {
  local https_url
  https_url=$(origin_as_https)
  exec git \
    -c "remote.origin.url=${https_url}" \
    -c "credential.helper=!f() { echo username=x-access-token; echo password=${TOKEN}; }; f" \
    "$@"
}

case "${1:-}" in
  token)
    echo "$TOKEN"
    ;;

  push)
    shift
    git_with_bot_creds push "$@"
    ;;

  pr-create)
    shift
    # Auto-ajoute le label claude-generated (convention projet)
    has_label=0
    for arg in "$@"; do
      if [[ "$arg" == "--label" || "$arg" == -l ]]; then has_label=1; break; fi
    done
    if [[ $has_label -eq 0 ]]; then
      set -- "$@" --label claude-generated
    fi
    exec gh pr create "$@"
    ;;

  exec)
    shift
    if [[ $# -eq 0 ]]; then
      echo "Erreur : 'exec' requiert une commande." >&2
      usage >&2
      exit 1
    fi
    exec "$@"
    ;;

  -h|--help|help)
    usage
    ;;

  *)
    echo "Erreur : sous-commande inconnue : $1" >&2
    usage >&2
    exit 1
    ;;
esac
