#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

IMAGE_NAME="${IMAGE_NAME:-fluxura:latest}"

printf "[docker] Build immagine applicativa: %s\n" "$IMAGE_NAME"
docker build -t "$IMAGE_NAME" .

printf "[docker] Avvio servizi di supporto (PostgreSQL, Redis, RabbitMQ, Flower)\n"
docker compose up -d postgres redis rabbitmq flower

printf "[docker] Avvio worker Fluxura in container dedicato\n"
docker rm -f fluxura-worker >/dev/null 2>&1 || true
docker run -d \
  --name fluxura-worker \
  --network fluxura_default \
  -e FLUXURA_DATABASE_URL="postgresql+psycopg://fluxura:fluxura@postgres:5432/fluxura" \
  -e FLUXURA_CELERY_BROKER_URL="redis://redis:6379/0" \
  -e FLUXURA_CELERY_RESULT_BACKEND="redis://redis:6379/1" \
  "$IMAGE_NAME"

printf "\nInstallazione completata.\n"
printf "- Flower: http://localhost:5555\n"
printf "- RabbitMQ UI: http://localhost:15672 (admin/admin)\n"
printf "- Logs worker: docker logs -f fluxura-worker\n"
