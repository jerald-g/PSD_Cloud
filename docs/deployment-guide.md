# PSD Cloud – Kubernetes Deployment Guide

This guide covers deploying the PSD Cloud Security Platform to a Kubernetes cluster using raw manifests.

## Prerequisites

- Kubernetes cluster (v1.27+) – Minikube, k3s, EKS, AKS, or GKE
- `kubectl` configured for your cluster
- Docker images built locally (or pushed to a container registry)

## Option 1: Raw Kubernetes Manifests

For local development or any Kubernetes environment.

### 1. Build Images Locally (Minikube)

```bash
# Point Docker to Minikube's daemon
eval $(minikube docker-env)

# Build all services (imagePullPolicy: Never in manifests)
for svc in auth-service scan-orchestrator sast-scanner dast-scanner \
           compliance-engine report-generator \
           api-gateway dashboard; do
  docker build -t psd-cloud/$svc:latest services/$svc/
done
```

### 2. Apply Manifests

```bash
# Create namespace and secrets
kubectl apply -f kubernetes/namespace.yaml

# Deploy backing services (PostgreSQL, Redis, NATS, MinIO)
kubectl apply -f kubernetes/backing-services.yaml

# Wait for backing services to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n psd-cloud --timeout=120s
kubectl wait --for=condition=ready pod -l app=redis -n psd-cloud --timeout=60s
kubectl wait --for=condition=ready pod -l app=nats -n psd-cloud --timeout=60s

# Deploy application microservices
kubectl apply -f kubernetes/microservices.yaml

# Deploy ingress (optional)
kubectl apply -f kubernetes/ingress.yaml
```

### 3. Access via NodePort

The raw manifests expose services via NodePort:

```bash
# Get the Minikube IP
minikube ip

# Access:
# Dashboard:   http://<minikube-ip>:30000
# API Gateway: http://<minikube-ip>:30080
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| Pods in `CrashLoopBackOff` | Check logs: `kubectl logs <pod> -n psd-cloud` |
| Database connection refused | Ensure PostgreSQL pod is ready: `kubectl get pods -l app=postgres -n psd-cloud` |
| NATS connection timeout | Verify NATS is running: `kubectl get pods -l app=nats -n psd-cloud` |
| Images not found (Minikube) | Run `eval $(minikube docker-env)` before building |
