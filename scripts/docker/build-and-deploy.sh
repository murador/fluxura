#!/usr/bin/env bash

################################################################################
# Script di Build, Push e Deploy Docker su Kubernetes per Fluxura
#
# DESCRIZIONE:
#   Questo script automatizza l'intero ciclo di vita dell'immagine Docker:
#   1. Costruisce l'immagine Docker localmente
#   2. La pushes su Docker Hub
#   3. Avvia il deploy su Kubernetes
#   4. Verifica lo stato dei pod
#
# PREREQUISITI:
#   - Docker (per la costruzione dell'immagine)
#   - Docker Hub account con credenziali configurate (docker login)
#   - kubectl (per l'interazione con il cluster Kubernetes)
#   - Un cluster Kubernetes raggiungibile e configurato in kubeconfig
#
# VARIABILI D'AMBIENTE:
#   - DOCKER_USERNAME: Username Docker Hub (required)
#   - IMAGE_TAG: Tag dell'immagine (default: latest)
#     Esempio: DOCKER_USERNAME=myuser IMAGE_TAG=v1.0.0 ./build-and-deploy.sh
#
# UTILIZZO:
#   1. Build, push e deploy standard:
#      DOCKER_USERNAME=your-username ./scripts/docker/build-and-deploy.sh
#
#   2. Con versione specifica:
#      DOCKER_USERNAME=your-username IMAGE_TAG=v1.1.0 ./scripts/docker/build-and-deploy.sh
#
#   3. Solo build (senza push e deploy):
#      DOCKER_USERNAME=your-username IMAGE_TAG=v1.1.0 ./scripts/docker/build-and-deploy.sh --build-only
#
#   4. Solo deploy (immagine già su Docker Hub):
#      DOCKER_USERNAME=your-username IMAGE_TAG=v1.1.0 ./scripts/docker/build-and-deploy.sh --deploy-only
#
# FLUSSO DI ESECUZIONE:
#   1. Valida i prerequisiti (Docker, kubectl, DOCKER_USERNAME)
#   2. Calcola il percorso root del progetto
#   3. Costruisce l'immagine Docker
#   4. Pushes su Docker Hub (a meno di --build-only)
#   5. Aggiorna anche il tag :latest (a meno di --build-only)
#   6. Avvia il deploy su Kubernetes (a meno di --build-only e --deploy-only)
#   7. Verifica lo stato dei pod
#   8. Mostra le istruzioni per il debug
#
# OUTPUT:
#   Lo script stampa lo stato di ogni passaggio con colori per leggibilità
#
# NOTE:
#   - Lo script utilizza 'set -euo pipefail' per arrestarsi al primo errore
#   - Supporta tre modalità: full workflow, build-only, deploy-only
#   - I colori nei messaggi richiedono terminal ANSI-compatible
#
################################################################################

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Modalità strict
set -euo pipefail

################################################################################
# FUNZIONI HELPER
################################################################################

print_info() {
  printf "${BLUE}[INFO]${NC} %s\n" "$1"
}

print_success() {
  printf "${GREEN}[✓]${NC} %s\n" "$1"
}

print_error() {
  printf "${RED}[✗]${NC} %s\n" "$1" >&2
}

print_warning() {
  printf "${YELLOW}[!]${NC} %s\n" "$1"
}

check_command() {
  if ! command -v "$1" &> /dev/null; then
    print_error "$1 non trovato. Installa $1 e riprova."
    exit 1
  fi
}

################################################################################
# PASSO 1: Validazione prerequisiti
################################################################################

print_info "Validazione prerequisiti..."

check_command docker
check_command kubectl

if [ -z "${DOCKER_USERNAME:-}" ]; then
  print_error "DOCKER_USERNAME non impostato. Usa: DOCKER_USERNAME=your-username $0"
  exit 1
fi

print_success "Docker installato"
print_success "kubectl installato"
print_success "DOCKER_USERNAME impostato: $DOCKER_USERNAME"

################################################################################
# PASSO 2: Configurazione percorsi e variabili
################################################################################

# Calcola il percorso assoluto della root del progetto
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# Configurazione immagine Docker
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE_NAME="$DOCKER_USERNAME/fluxura:$IMAGE_TAG"
DEPLOY_SCRIPT="$ROOT_DIR/scripts/k8s/deploy.sh"

print_info "Root directory: $ROOT_DIR"
print_info "Nome immagine: $IMAGE_NAME"

################################################################################
# PASSO 3: Parsing opzioni
################################################################################

BUILD_ONLY=false
DEPLOY_ONLY=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --build-only)
      BUILD_ONLY=true
      shift
      ;;
    --deploy-only)
      DEPLOY_ONLY=true
      shift
      ;;
    *)
      print_error "Opzione sconosciuta: $1"
      exit 1
      ;;
  esac
done

################################################################################
# PASSO 4: Build dell'immagine Docker
################################################################################

print_info "Build dell'immagine Docker..."
docker build -t "$IMAGE_NAME" .
print_success "Build completato: $IMAGE_NAME"

################################################################################
# PASSO 5: Push su Docker Hub (se non --build-only)
################################################################################

if [ "$BUILD_ONLY" = false ]; then
  print_info "Push dell'immagine su Docker Hub..."
  docker push "$IMAGE_NAME"
  print_success "Push completato: $IMAGE_NAME"

  # Se non è latest, aggiorna anche il tag latest
  if [ "$IMAGE_TAG" != "latest" ]; then
    print_info "Aggiornamento tag :latest..."
    docker tag "$IMAGE_NAME" "$DOCKER_USERNAME/fluxura:latest"
    docker push "$DOCKER_USERNAME/fluxura:latest"
    print_success "Tag :latest aggiornato"
  fi
fi

################################################################################
# PASSO 6: Deploy su Kubernetes (se non --build-only e non --deploy-only)
################################################################################

if [ "$BUILD_ONLY" = false ] && [ "$DEPLOY_ONLY" = false ]; then
  print_info "Deploy su Kubernetes..."
  
  if [ ! -f "$DEPLOY_SCRIPT" ]; then
    print_error "Script di deploy non trovato: $DEPLOY_SCRIPT"
    exit 1
  fi
  
  IMAGE_NAME="$IMAGE_NAME" bash "$DEPLOY_SCRIPT"
  print_success "Deploy completato"
fi

################################################################################
# PASSO 7: Verifica stato pod (se deploy eseguito)
################################################################################

if [ "$BUILD_ONLY" = false ]; then
  print_info "Verifica stato pod..."
  sleep 2
  
  kubectl -n fluxura get pods
  
  print_info "Attendimento che i pod siano in Running..."
  if kubectl wait --for=condition=ready pod -l app=fluxura-worker -n fluxura --timeout=120s 2>/dev/null; then
    print_success "Pod fluxura-worker è in Running!"
  else
    print_warning "Timeout in attesa dei pod. Verifica con: kubectl -n fluxura get pods"
  fi
fi

################################################################################
# PASSO 8: Istruzioni post-deploy
################################################################################

printf "\n${GREEN}════════════════════════════════════════════════════════════${NC}\n"
print_success "Processo completato!"
printf "${GREEN}════════════════════════════════════════════════════════════${NC}\n\n"

if [ "$BUILD_ONLY" = false ]; then
  print_info "Comandi utili per il debug:"
  printf "  ${YELLOW}Log del worker:${NC}\n"
  printf "    kubectl -n fluxura logs deployment/fluxura-worker -f\n\n"
  
  printf "  ${YELLOW}Accesso al pod:${NC}\n"
  printf "    kubectl exec -it \$(kubectl get pod -l app=fluxura-worker -n fluxura -o jsonpath='{.items[0].metadata.name}') -n fluxura -- /bin/bash\n\n"
  
  printf "  ${YELLOW}Port-forward Flower (monitoring):${NC}\n"
  printf "    kubectl -n fluxura port-forward svc/flower 5555:5555\n"
  printf "    Accedi a: http://localhost:5555\n\n"
  
  printf "  ${YELLOW}Stato pod:${NC}\n"
  printf "    kubectl -n fluxura get pods\n\n"
fi

print_info "Per il prossimo aggiornamento:"
printf "  DOCKER_USERNAME=$DOCKER_USERNAME IMAGE_TAG=v1.1.0 $0\n"
