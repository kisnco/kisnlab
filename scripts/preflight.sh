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

# Résultat
echo ""
echo "========================="
echo "  ✓ $PASS checks OK"
[ "$FAIL" -gt 0 ] && echo "  ✗ $FAIL checks KO" && echo "" && exit 1
echo ""
echo "  Prêt à lancer : docker compose up -d"
echo ""