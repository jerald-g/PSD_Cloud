#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# PSD Cloud – Deploy to Local Kubernetes (Docker Desktop)
#
# Prerequisites:
#   1. Docker Desktop with Kubernetes enabled
#   2. kubectl installed
#
# Usage:
#   bash kubernetes/deploy-local.sh
# ═══════════════════════════════════════════════════════════════════════════════

set -e
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "============================================"
echo " PSD Cloud – Kubernetes Deployment"
echo "============================================"
echo ""

# ─── Step 1: Verify Kubernetes is running ─────────────────────────────────────
echo "[1/7] Checking Kubernetes connection..."
if ! kubectl cluster-info &>/dev/null; then
    echo "ERROR: Cannot connect to Kubernetes."
    echo "       Open Docker Desktop → Settings → Kubernetes → Enable Kubernetes"
    echo "       Then wait for the green dot and try again."
    exit 1
fi
echo "  ✓ Kubernetes is running"
echo ""

# ─── Step 2: Build Docker images locally ──────────────────────────────────────
echo "[2/7] Building Docker images (this takes a few minutes the first time)..."
SERVICES="auth-service api-gateway scan-orchestrator sast-scanner dast-scanner compliance-engine report-generator dashboard"

for svc in $SERVICES; do
    echo "  Building psd-cloud/$svc ..."
    docker build -t "psd-cloud/$svc:latest" "$ROOT_DIR/services/$svc" -q
done
echo "  ✓ All 8 images built"
echo ""

# ─── Step 3: Create namespace ─────────────────────────────────────────────────
echo "[3/7] Creating Kubernetes namespace..."
kubectl apply -f kubernetes/namespace.yaml
echo "  ✓ Namespace 'psd-cloud' created"
echo ""

# ─── Step 4: Deploy backing services ──────────────────────────────────────────
echo "[4/7] Deploying backing services (PostgreSQL, Redis, NATS, MinIO, SonarQube, ZAP, Prometheus, Grafana)..."
kubectl apply -f kubernetes/backing-services.yaml
echo "  ✓ Backing services deployed"
echo ""

# ─── Step 5: Wait for backing services to be ready ────────────────────────────
echo "[5/7] Waiting for backing services to be ready (this may take 1-2 minutes)..."
kubectl wait --namespace psd-cloud --for=condition=ready pod -l app=postgres --timeout=120s 2>/dev/null || true
kubectl wait --namespace psd-cloud --for=condition=ready pod -l app=redis --timeout=60s 2>/dev/null || true
kubectl wait --namespace psd-cloud --for=condition=ready pod -l app=nats --timeout=60s 2>/dev/null || true
kubectl wait --namespace psd-cloud --for=condition=ready pod -l app=minio --timeout=60s 2>/dev/null || true
kubectl wait --namespace psd-cloud --for=condition=ready pod -l app=sonarqube --timeout=180s 2>/dev/null || true
echo "  ✓ Backing services ready"
echo ""

# ─── Step 6: Wait for init jobs ──────────────────────────────────────────────
echo "[6/7] Waiting for init jobs (SonarQube config, MinIO bucket)..."
kubectl wait --namespace psd-cloud --for=condition=complete job/minio-init --timeout=120s 2>/dev/null || true
kubectl wait --namespace psd-cloud --for=condition=complete job/sonarqube-init --timeout=180s 2>/dev/null || true
echo "  ✓ Init jobs complete"
echo ""

# ─── Step 7: Deploy microservices ─────────────────────────────────────────────
echo "[7/7] Deploying PSD Cloud microservices..."
kubectl apply -f kubernetes/microservices.yaml
echo "  ✓ All microservices deployed"
echo ""

# ─── Done ─────────────────────────────────────────────────────────────────────
echo "============================================"
echo " Deployment complete!"
echo "============================================"
echo ""
echo "Waiting for pods to start..."
sleep 10
kubectl get pods -n psd-cloud
echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║ Access the services:                                  ║"
echo "║                                                       ║"
echo "║   Dashboard:     http://localhost:30000                ║"
echo "║   API Gateway:   http://localhost:30080                ║"
echo "║   SonarQube:     http://localhost:30900                ║"
echo "║   MinIO Console: http://localhost:30901                ║"
echo "║   Grafana:       http://localhost:30300                ║"
echo "║   Prometheus:    http://localhost:30090                ║"
echo "║                                                       ║"
echo "║ Useful commands:                                      ║"
echo "║   kubectl get pods -n psd-cloud                       ║"
echo "║   kubectl get svc -n psd-cloud                        ║"
echo "║   kubectl logs -n psd-cloud <pod-name>                ║"
echo "║   kubectl describe pod -n psd-cloud <pod-name>        ║"
echo "║                                                       ║"
echo "║ To tear down:                                         ║"
echo "║   kubectl delete namespace psd-cloud                  ║"
echo "╚═══════════════════════════════════════════════════════╝"
