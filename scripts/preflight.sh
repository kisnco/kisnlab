#!/usr/bin/env bash
# Vérifie que l'environnement KisnLab est prêt avant docker compose up
set -euo pipefail

PASS=0
FAIL=0

ok()   { echo "  ✓ $1"; PASS=$((PASS + 1)); }
fail() { echo "  ✗ $1"; FAIL=$((FAIL + 1)); }
warn() { echo "  ~ $1"; }

echo ""
echo "=== KisnLab preflight ==="
echo ""

# /etc/hosts
echo "[ /etc/hosts ]"
for domain in openclaw.kisnlab.local n8n.kisnlab.local langfuse.kisnlab.local traefik.kisnlab.local; do
  grep -q "$domain" /etc/hosts && ok "$domain" || fail "$domain manquant — ajoute : 127.0.0.1 $domain"
done

# Docker
echo ""
echo "[ Docker ]"
docker info > /dev/null 2>&1 && ok "Docker daemon running" || fail "Docker non démarré"

# .env
echo ""
echo "[ .env ]"
if [ ! -f .env ]; then
  fail ".env manquant — cp .env.example .env"
else
  ok ".env présent"
  REQUIRED_VARS=(
    TRAEFIK_DASHBOARD_AUTH
    ANTHROPIC_API_KEY
    DISCORD_BOT_TOKEN
    DISCORD_GUILD_ID
    DISCORD_YOUR_USER_ID
    DISCORD_CHANNEL_DEV
    DISCORD_CHANNEL_COMMERCIAL
    DISCORD_CHANNEL_ADMIN
    DISCORD_CHANNEL_COMM
    DISCORD_CHANNEL_STRATEGIE
    DISCORD_CHANNEL_ALERTES
    DISCORD_CHANNEL_BRIEFS
    DISCORD_CHANNEL_LOGS
    POSTGRES_USER
    POSTGRES_PASSWORD
    POSTGRES_DB
    REDIS_PASSWORD
    N8N_ENCRYPTION_KEY
    LANGFUSE_SECRET
    LANGFUSE_SALT
    OPENCLAW_WEBHOOK_SECRET
    GITHUB_TOKEN
    DISCORD_WEBHOOK_ALERTES
    DISCORD_WEBHOOK_BRIEFS
    DISCORD_WEBHOOK_LOGS
    DISCORD_WEBHOOK_ADMIN
  )
  for var in "${REQUIRED_VARS[@]}"; do
    val=$(grep -E "^${var}=" .env | cut -d= -f2- || true)
    if [ -z "$val" ] || echo "$val" | grep -q "CHANGE_ME"; then
      fail "$var non renseigné"
    else
      ok "$var"
    fi
  done
fi

# Script postgres
echo ""
echo "[ Scripts ]"
[ -x config/postgres/init-multiple-dbs.sh ] && ok "init-multiple-dbs.sh exécutable" || fail "init-multiple-dbs.sh non exécutable — chmod +x config/postgres/init-multiple-dbs.sh"
[ -x scripts/setup-branch-protection.sh ] && ok "setup-branch-protection.sh exécutable" || warn "setup-branch-protection.sh non exécutable (optionnel — chmod +x si besoin)"

# Bind mount volumes — créer les dossiers si absents (Docker ne le fait pas pour les bind mounts déclaratifs)
echo ""
echo "[ Volumes (./volumes/) ]"
for dir in postgres redis n8n clickhouse openclaw openclaw-workspace openclaw-dind-data openclaw-dind-certs-ca openclaw-dind-certs-client; do
  if [ -d "volumes/${dir}" ]; then
    ok "volumes/${dir}"
  else
    mkdir -p "volumes/${dir}" && ok "volumes/${dir} (créé)"
  fi
done

# Sécurité OpenClaw — vérifier que le socket Docker du host n'est PAS monté
echo ""
echo "[ Sécurité OpenClaw ]"
if [ -f Dockerfile.openclaw ]; then
  ok "Dockerfile.openclaw présent"
else
  fail "Dockerfile.openclaw manquant — image custom non construite"
fi

# Si openclaw tourne, vérifier les invariants critiques
if docker inspect kisnlab-openclaw >/dev/null 2>&1; then
  if docker inspect kisnlab-openclaw --format '{{range .Mounts}}{{.Source}}{{"\n"}}{{end}}' | grep -q "/var/run/docker.sock"; then
    fail "kisnlab-openclaw monte /var/run/docker.sock — RISQUE CRITIQUE, à retirer"
  else
    ok "kisnlab-openclaw ne monte PAS le socket Docker du host"
  fi

  if docker inspect kisnlab-openclaw --format '{{range .Mounts}}{{if eq .Destination "/repo/kisnlab"}}{{.Mode}}{{end}}{{end}}' | grep -q "ro"; then
    ok "/repo/kisnlab monté en lecture seule"
  else
    warn "/repo/kisnlab pas en lecture seule (le container ne tourne peut-être pas encore avec la nouvelle config)"
  fi

  if docker exec kisnlab-openclaw which docker >/dev/null 2>&1; then
    ok "docker CLI présent dans openclaw"
  else
    fail "docker CLI absent — rebuild avec docker compose build openclaw"
  fi

  if docker exec kisnlab-openclaw which gh >/dev/null 2>&1; then
    ok "gh CLI présent dans openclaw"
  else
    fail "gh CLI absent — rebuild avec docker compose build openclaw"
  fi
else
  warn "kisnlab-openclaw pas démarré — checks runtime skippés (lance docker compose up -d --build)"
fi

# Résultat
echo ""
echo "========================="
echo "  ✓ $PASS checks OK"
[ "$FAIL" -gt 0 ] && echo "  ✗ $FAIL checks KO" && echo "" && exit 1
echo ""
echo "  Prêt à lancer : docker compose up -d"
echo ""