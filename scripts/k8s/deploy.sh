#!/usr/bin/env bash

################################################################################
# Script di Deploy Kubernetes per Fluxura
# 
# DESCRIZIONE:
#   Questo script automatizza il deployment dell'applicazione Fluxura su 
#   Kubernetes. Gestisce la costruzione dell'immagine Docker, il caricamento 
#   su cluster kind (se disponibile) e l'applicazione di tutti i manifest 
#   Kubernetes necessari.
#
# PREREQUISITI:
#   - Docker (per la costruzione dell'immagine)
#   - kubectl (per l'interazione con il cluster Kubernetes)
#   - kind (opzionale, per cluster locali di sviluppo)
#   - Un cluster Kubernetes raggiungibile e configurato in kubeconfig
#
# VARIABILI D'AMBIENTE:
#   - IMAGE_NAME: Nome e tag dell'immagine Docker (default: fluxura:latest)
#     Esempio: IMAGE_NAME=fluxura:v1.0.0 ./deploy.sh
#
# UTILIZZO:
#   1. Deploy standard su cluster remoto:
#      ./scripts/k8s/deploy.sh
#
#   2. Deploy con immagine personalizzata:
#      IMAGE_NAME=fluxura:custom ./scripts/k8s/deploy.sh
#
#   3. Deploy su cluster kind locale:
#      ./scripts/k8s/deploy.sh
#      (lo script rilevava automaticamente kind e carica l'immagine)
#
# FLUSSO DI ESECUZIONE:
#   1. Calcola la directory root del progetto
#   2. Costruisce l'immagine Docker
#   3. Carica l'immagine su cluster kind (se disponibile)
#   4. Applica tutti i manifest Kubernetes in ordine
#   5. Aggiorna l'immagine del deployment worker
#   6. Mostra istruzioni post-deploy
#
# OUTPUT:
#   Lo script stampa lo stato di cada passaggio e istruzioni utili per:
#   - Accedere a Flower (task monitoring)
#   - Verificare lo stato dei pod
#
# NOTE:
#   - Lo script utilizza 'set -euo pipefail' per arrestarsi al primo errore
#   - Il caricamento su kind usa '|| true' per non fallire se kind non è disponibile
#   - Il namespace 'fluxura' deve essere creato da k8s/namespace.yaml
#   - L'ordine di applicazione dei manifest è importante per le dipendenze
#
################################################################################

# Modalità strict: exit al primo errore, variabili non definite causano errore,
# pipe fail se qualsiasi comando fallisce
set -euo pipefail

################################################################################
# PASSO 1: Configurazione e setup percorsi
################################################################################

# Calcola il percorso assoluto della directory root del progetto
# - ${BASH_SOURCE[0]}: percorso dello script corrente
# - dirname: estrae la directory dello script (scripts/k8s)
# - /../..: risale di 2 livelli (raggiungiamo la root del progetto)
# - pwd: converte a percorso assoluto
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Cambia directory alla root del progetto per gli accessi ai file
cd "$ROOT_DIR"

################################################################################
# PASSO 2: Configurazione immagine Docker
################################################################################

# Imposta il nome/tag dell'immagine Docker
# Usa la variabile d'ambiente IMAGE_NAME se fornita, altrimenti 'fluxura:latest'
# Sintassi: ${VAR:-default} utilizza default se VAR non è definita
IMAGE_NAME="${IMAGE_NAME:-fluxura:latest}"

################################################################################
# PASSO 3: Build dell'immagine Docker
################################################################################

# Stampa messaggio di inizio build (usando printf per compatibilità)
printf "[k8s] Build immagine locale: %s\n" "$IMAGE_NAME"

# Costruisce l'immagine Docker dalla Dockerfile nella root del progetto
# - -t: assegna il tag all'immagine
# - .: Dockerfile nella directory corrente (root del progetto)
docker build -t "$IMAGE_NAME" .

################################################################################
# PASSO 4: Caricamento immagine su cluster kind (opzionale)
################################################################################

# Controlla se il comando 'kind' è disponibile nel PATH
# command -v kind >/dev/null 2>&1 ritorna 0 se kind esiste, 1 altrimenti
if command -v kind >/dev/null 2>&1; then
  # Se kind è installato, carica l'immagine nel cluster kind
  printf "[k8s] Caricamento immagine su kind\n"
  
  # Carica l'immagine Docker nel cluster kind locale
  # || true: ignora gli errori (non fallisce se kind non è configurato)
  # Questo permette allo script di continuare anche se kind fallisce
  kind load docker-image "$IMAGE_NAME" || true
fi

################################################################################
# PASSO 5: Applicazione dei manifest Kubernetes
################################################################################

# Stampa messaggio di inizio applicazione manifest
printf "[k8s] Applico manifest\n"

# Applica i manifest in ordine di dipendenza:

# 1. Crea il namespace 'fluxura' (deve essere primo)
kubectl apply -f k8s/namespace.yaml

# 2. Applica ConfigMap con configurazioni dell'applicazione
kubectl apply -f k8s/configmap.yaml

# 3. Deploya il database PostgreSQL (dipendenza per l'app)
kubectl apply -f k8s/postgres.yaml

# 4. Deploya Redis (cache/session store)
kubectl apply -f k8s/redis.yaml

# 5. Deploya RabbitMQ (message broker per worker async)
kubectl apply -f k8s/rabbitmq.yaml

# 6. Applica la configurazione del deployment worker
kubectl apply -f k8s/worker.yaml

# 7. Aggiorna l'immagine del deployment worker con quella appena costruita
# - -n fluxura: specifica il namespace
# - set image: aggiorna l'immagine di un container
# - deployment/fluxura-worker: il deployment da aggiornare
# - worker=: il container che deve utilizzare la nuova immagine
kubectl -n fluxura set image deployment/fluxura-worker worker="$IMAGE_NAME"

# 8. Deploya Flower (interfaccia web per monitorare i task Celery)
kubectl apply -f k8s/flower.yaml

################################################################################
# PASSO 6: Messagi post-deploy e istruzioni d'uso
################################################################################

# Riga vuota per leggibilità
printf "\nDeploy completato.\n"

# Istruzione per accedere all'interfaccia Flower (monitoring Celery)
# Flower è accessibile su localhost:5555 una volta eseguito il port-forward
printf "Port-forward Flower: kubectl -n fluxura port-forward svc/flower 5555:5555\n"

# Istruzione per visualizzare lo stato di tutti i pod deployati
# Mostra il nome, stato, numero di restart e uptime di ogni pod
printf "Stato pod: kubectl -n fluxura get pods\n"
