# Versione semplificata dello script di build.
# Build locale
docker build -t your-username/fluxura:latest .

# Test locale (opzionale)
docker run -it your-username/fluxura:latest

# Push su Docker Hub
docker push your-username/fluxura:latest

# Deploy su Kubernetes
IMAGE_NAME=your-username/fluxura:latest ./scripts/k8s/deploy.sh

# Verifica stato
kubectl -n fluxura get pods
