#!/bin/bash

# create-secrets.sh - Create Kubernetes secrets for movie recommendation backend
# Run this script to create all necessary secrets

set -e

NAMESPACE="movie-recommendation"

echo "🔐 Creating Kubernetes secrets for Movie Recommendation Backend..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if namespace exists
if ! kubectl get namespace $NAMESPACE &> /dev/null; then
    log_warn "Namespace $NAMESPACE does not exist. Creating it..."
    kubectl create namespace $NAMESPACE
fi

# Generate random passwords if not set
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-$(openssl rand -base64 32)}
DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY:-$(openssl rand -base64 50)}
SENTRY_DSN=${SENTRY_DSN:-""}
DATABASE_URL="postgresql://movie_user:${POSTGRES_PASSWORD}@postgres-service:5432/movie_recommendation_db"

log_info "Creating database secret..."
kubectl create secret generic movie-recommendation-db-secret \
    --namespace=$NAMESPACE \
    --from-literal=POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
    --from-literal=DATABASE_URL="$DATABASE_URL" \
    --dry-run=client -o yaml | kubectl apply -f -

log_info "Creating application secret..."
kubectl create secret generic movie-recommendation-app-secret \
    --namespace=$NAMESPACE \
    --from-literal=SECRET_KEY="$DJANGO_SECRET_KEY" \
    --from-literal=SENTRY_DSN="$SENTRY_DSN" \
    --dry-run=client -o yaml | kubectl apply -f -

# Optional: Create Docker registry secret if using private registry
if [ ! -z "$DOCKER_USERNAME" ] && [ ! -z "$DOCKER_PASSWORD" ] && [ ! -z "$DOCKER_EMAIL" ]; then
    log_info "Creating Docker registry secret..."
    kubectl create secret docker-registry movie-recommendation-registry-secret \
        --namespace=$NAMESPACE \
        --docker-server=https://index.docker.io/v1/ \
        --docker-username="$DOCKER_USERNAME" \
        --docker-password="$DOCKER_PASSWORD" \
        --docker-email="$DOCKER_EMAIL" \
        --dry-run=client -o yaml | kubectl apply -f -
fi

# Optional: Create TLS secret for HTTPS
if [ -f "tls.crt" ] && [ -f "tls.key" ]; then
    log_info "Creating TLS secret..."
    kubectl create secret tls movie-recommendation-tls-secret \
        --namespace=$NAMESPACE \
        --cert=tls.crt \
        --key=tls.key \
        --dry-run=client -o yaml | kubectl apply -f -
fi

log_info "✅ Secrets created successfully!"

echo ""
echo "📋 Summary of created secrets:"
kubectl get secrets -n $NAMESPACE | grep movie-recommendation

echo ""
echo "🔑 Passwords generated:"
echo "PostgreSQL Password: $POSTGRES_PASSWORD"
echo "Django Secret Key: $DJANGO_SECRET_KEY"

echo ""
echo "💡 To delete all secrets:"
echo "kubectl delete secrets -n $NAMESPACE -l app=movie-recommendation-backend"

echo ""
echo "⚠️  IMPORTANT: Save these passwords securely!"
echo "   You can also set them as environment variables before running this script:"
echo "   export POSTGRES_PASSWORD='your-secure-password'"
echo "   export DJANGO_SECRET_KEY='your-secret-key'"
echo "   export SENTRY_DSN='your-sentry-dsn'"