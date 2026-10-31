#!/usr/bin/env bash
# Avvio automatico di Fluxura su Killercoda: wrapper attorno a scripts/k8s/deploy.sh.
# Uso: bash scripts/killercoda/start.sh
# Oppure: curl -fsSL https://raw.githubusercontent.com/murador/fluxura/main/scripts/killercoda/start.sh | bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/murador/fluxura.git}"
BRANCH="${BRANCH:-main}"
IMAGE_NAME="${IMAGE_NAME:-fluxura:latest}"
WORKDIR="${WORKDIR:-$HOME/fluxura}"
export IMAGE_NAME

log() { printf "\n[killercoda] %s\n" "$*"; }

log "Attendo che il cluster Kubernetes sia pronto"
until kubectl get nodes >/dev/null 2>&1; do sleep 3; done
kubectl wait --for=condition=Ready nodes --all --timeout=300s

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/../k8s/deploy.sh" ]; then
  WORKDIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
elif [ -d "$WORKDIR/.git" ]; then
  git -C "$WORKDIR" pull --ff-only
else
  log "Clono $REPO_URL ($BRANCH)"
  git clone --depth 1 -b "$BRANCH" "$REPO_URL" "$WORKDIR"
fi
cd "$WORKDIR"

# deploy.sh costruisce l'immagine con Docker ma la carica solo su kind:
# su Killercoda (containerd) la importo io, poi la build di deploy.sh sarà tutta in cache.
log "Build e import immagine in containerd"
docker build -t "$IMAGE_NAME" .
if command -v ctr >/dev/null 2>&1; then
  docker save "$IMAGE_NAME" | ctr -n k8s.io images import -
fi

log "Eseguo scripts/k8s/deploy.sh"
bash scripts/k8s/deploy.sh

# Con tag :latest Kubernetes tenterebbe il pull: uso l'immagine locale.
kubectl -n fluxura patch deployment fluxura-worker --type=json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/imagePullPolicy","value":"IfNotPresent"}]'

log "Attendo i deployment"
for d in $(kubectl -n fluxura get deploy -o name); do
  kubectl -n fluxura rollout status "$d" --timeout=300s || true
done

log "Port-forward Flower su 0.0.0.0:5555"
nohup kubectl -n fluxura port-forward --address 0.0.0.0 svc/flower 5555:5555 >/tmp/flower-pf.log 2>&1 &

kubectl -n fluxura get pods
log "Fatto. Apri Flower da Killercoda: menu Traffic/Ports -> 5555"
