#!/usr/bin/env bash
# Génère un installation token GitHub App (durée de vie : 1h)
#
# Usage:
#   ./scripts/gh-app-token.sh                        # utilise APP_NAME par défaut
#   ./scripts/gh-app-token.sh kisnlab-claude-code    # utilise une App spécifique
#
# Lit la config dans ~/.claude/secrets/<APP_NAME>.env :
#   GH_APP_ID=...
#   GH_INSTALLATION_ID=...
#
# Lit la clé privée dans ~/.claude/secrets/<APP_NAME>.private-key.pem
#
# Sortie : le token sur stdout (à utiliser dans GITHUB_TOKEN / GH_TOKEN)

set -euo pipefail

APP_NAME="${1:-${GH_APP_NAME:-kisnlab-claude-code}}"
SECRETS_DIR="${HOME}/.claude/secrets"
CONFIG_FILE="${SECRETS_DIR}/${APP_NAME}.env"
PEM_FILE="${SECRETS_DIR}/${APP_NAME}.private-key.pem"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Erreur : config introuvable : $CONFIG_FILE" >&2
  exit 1
fi

if [[ ! -f "$PEM_FILE" ]]; then
  echo "Erreur : clé privée introuvable : $PEM_FILE" >&2
  echo "Place le .pem téléchargé depuis GitHub à cet emplacement." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$CONFIG_FILE"
: "${GH_APP_ID:?GH_APP_ID manquant dans $CONFIG_FILE}"
: "${GH_INSTALLATION_ID:?GH_INSTALLATION_ID manquant dans $CONFIG_FILE}"

# Encode base64url (sans padding ni saut de ligne)
b64url() { openssl base64 -A | tr -d '=' | tr '/+' '_-'; }

# JWT header + payload (iat -60s pour tolérance de drift, exp +9min, max 10min)
now=$(date +%s)
iat=$((now - 60))
exp=$((now + 540))

header=$(printf '{"alg":"RS256","typ":"JWT"}' | b64url)
payload=$(printf '{"iat":%d,"exp":%d,"iss":"%s"}' "$iat" "$exp" "$GH_APP_ID" | b64url)
signing_input="${header}.${payload}"
signature=$(printf '%s' "$signing_input" \
  | openssl dgst -sha256 -sign "$PEM_FILE" -binary \
  | b64url)
jwt="${signing_input}.${signature}"

# Échange JWT → installation token
response=$(curl -sS -X POST \
  -H "Authorization: Bearer ${jwt}" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/app/installations/${GH_INSTALLATION_ID}/access_tokens")

token=$(echo "$response" | jq -r '.token // empty')

if [[ -z "$token" ]]; then
  echo "Erreur : échec récupération token. Réponse API :" >&2
  echo "$response" | jq . >&2 2>/dev/null || echo "$response" >&2
  exit 1
fi

echo "$token"
