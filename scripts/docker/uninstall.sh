#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

docker rm -f fluxura-worker >/dev/null 2>&1 || true
docker compose down

printf "Ambiente Docker Fluxura arrestato e rimosso.\n"
