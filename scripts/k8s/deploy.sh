#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

IMAGE_NAME="${IMAGE_NAME:-fluxura:latest}"

printf "[k8s] Build immagine locale: %s\n" "$IMAGE_NAME"
docker build -t "$IMAGE_NAME" .

if command -v kind >/dev/null 2>&1; then
  printf "[k8s] Caricamento immagine su kind\n"
  kind load docker-image "$IMAGE_NAME" || true
fi

printf "[k8s] Applico manifest\n"
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/rabbitmq.yaml
sed "s|__IMAGE_NAME__|${IMAGE_NAME}|g" k8s/worker.yaml | kubectl apply -f -
kubectl apply -f k8s/flower.yaml

printf "\nDeploy completato.\n"
printf "Port-forward Flower: kubectl -n fluxura port-forward svc/flower 5555:5555\n"
printf "Stato pod: kubectl -n fluxura get pods\n"
