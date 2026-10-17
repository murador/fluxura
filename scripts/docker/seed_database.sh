#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
POSTGRES_SERVICE="${POSTGRES_SERVICE:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-fluxura}"
POSTGRES_USER="${POSTGRES_USER:-fluxura}"
SEED_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/seed_database.sql"

if ! command -v docker >/dev/null 2>&1; then
    echo "Errore: Docker non e' installato o non e' nel PATH." >&2
    exit 1
fi

if ! docker compose -f "$COMPOSE_FILE" ps --services --status running | grep -qx "$POSTGRES_SERVICE"; then
    echo "Il servizio PostgreSQL non e' attivo. Avvio il solo database..."
    docker compose -f "$COMPOSE_FILE" up -d "$POSTGRES_SERVICE"
fi

echo "Attendo PostgreSQL..."
for _ in $(seq 1 30); do
    if docker compose -f "$COMPOSE_FILE" exec -T "$POSTGRES_SERVICE" \
        pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
        break
    fi
    sleep 2
done

if ! docker compose -f "$COMPOSE_FILE" exec -T "$POSTGRES_SERVICE" \
    pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    echo "Errore: PostgreSQL non e' diventato disponibile." >&2
    exit 1
fi

docker compose -f "$COMPOSE_FILE" exec -T "$POSTGRES_SERVICE" \
    psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$SEED_FILE"

echo "Database popolato. Fatture demo disponibili: 1001 e 1002."
