#!/bin/bash
# =============================================================================
# KisnLab — Init Postgres : crée plusieurs bases + active pgvector sur chacune
# =============================================================================
set -e
set -u

function create_database() {
  local database=$1
  echo "  Creating database: $database"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE "$database";
    GRANT ALL PRIVILEGES ON DATABASE "$database" TO "$POSTGRES_USER";
EOSQL
  # Active pgvector sur chaque base
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$database" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
EOSQL
}

if [ -n "$POSTGRES_MULTIPLE_DATABASES" ]; then
  echo "==> Creating databases: $POSTGRES_MULTIPLE_DATABASES"
  for db in $(echo $POSTGRES_MULTIPLE_DATABASES | tr ',' ' '); do
    create_database $db
  done
  echo "==> All databases created ✅"
fi
