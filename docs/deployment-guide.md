# PSD Cloud – Kubernetes Deployment Guide

This guide covers deploying the PSD Cloud Security Platform to a Kubernetes cluster using either Helm charts or raw manifests.

## Prerequisites

- Kubernetes cluster (v1.27+) – Minikube, k3s, EKS, AKS, or GKE
- `kubectl` configured for your cluster
- `helm` v3.12+ (for Helm deployment)
- Docker images built and pushed to a container registry

## Option 1: Helm Deployment (Recommended)

### 1. Build and Push Docker Images

```bash
# Set your registry
export REGISTRY=your-registry.example.com/psd-cloud
export TAG=$(git rev-parse --short HEAD)

# Build all services
for svc in auth-service scan-orchestrator sast-scanner dast-scanner \
           compliance-engine report-generator notification-service \
           api-gateway dashboard; do
  docker build -t $REGISTRY/$svc:$TAG services/$svc/
  docker push $REGISTRY/$svc:$TAG
done
```

### 2. Install with Helm

```bash
# Update Helm dependencies (PostgreSQL, Redis, NATS, MinIO, Prometheus)
cd infra/helm
helm dependency update

# Deploy
helm upgrade --install psd-cloud . \
  --namespace psd-cloud \
  --create-namespace \
  --set global.imageRegistry=$REGISTRY \
  --set global.imageTag=$TAG \
  --set global.jwtSecret=$(openssl rand -base64 32) \
  --set postgresql.auth.password=$(openssl rand -base64 16) \
  --set minio.auth.rootPassword=$(openssl rand -base64 16)
```

### 3. Verify Deployment

```bash
kubectl get pods -n psd-cloud
kubectl get svc -n psd-cloud
```

All pods should reach `Running` status within 2-3 minutes.

### 4. Access the Platform

```bash
# Port-forward the API gateway
kubectl port-forward svc/psd-cloud-api-gateway 8080:8000 -n psd-cloud

# Port-forward the dashboard
kubectl port-forward svc/psd-cloud-dashboard 3000:80 -n psd-cloud
```

- Dashboard: http://localhost:3000
- API Gateway: http://localhost:8080

### Custom Values

Create a `values-production.yaml` to override defaults:

```yaml
global:
  imageRegistry: your-registry.example.com/psd-cloud
  imageTag: "v1.0.0"
  jwtSecret: ""           # Set via --set or external secret manager
  database:
    host: your-rds-endpoint.amazonaws.com   # Use managed database
  minio:
    endpoint: s3.amazonaws.com              # Use real S3

postgresql:
  enabled: false          # Disable bundled PostgreSQL when using managed DB

minio:
  enabled: false          # Disable bundled MinIO when using S3

apiGateway:
  ingress:
    enabled: true
    host: psd-cloud.yourdomain.com
    tls:
      - secretName: psd-cloud-tls
        hosts:
          - psd-cloud.yourdomain.com
```

```bash
helm upgrade --install psd-cloud infra/helm/ \
  -f values-production.yaml \
  --namespace psd-cloud
```

## Option 2: Raw Kubernetes Manifests

For local development or environments without Helm.

### 1. Build Images Locally (Minikube)

```bash
# Point Docker to Minikube's daemon
eval $(minikube docker-env)

# Build all services (imagePullPolicy: Never in manifests)
for svc in auth-service scan-orchestrator sast-scanner dast-scanner \
           compliance-engine report-generator notification-service \
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

## Option 3: Terraform + Helm (Cloud Provisioning)

Provision a cloud Kubernetes cluster first, then deploy with Helm.

```bash
# Provision infrastructure
cd infra/terraform
terraform init
terraform apply -var cloud_provider=aws    # or azure, gcp

# Get kubeconfig
aws eks update-kubeconfig --name $(terraform output -raw cluster_name)

# Deploy with Helm (as in Option 1)
cd ../../infra/helm
helm dependency update
helm upgrade --install psd-cloud . --namespace psd-cloud --create-namespace
```

## Monitoring

When `monitoring.enabled=true` (default), the Helm chart deploys Prometheus and Grafana via the kube-prometheus-stack subchart.

```bash
# Port-forward Grafana
kubectl port-forward svc/psd-cloud-grafana 3001:80 -n psd-cloud
# Default credentials: admin / prom-operator
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| Pods in `CrashLoopBackOff` | Check logs: `kubectl logs <pod> -n psd-cloud` |
| Database connection refused | Ensure PostgreSQL pod is ready: `kubectl get pods -l app=postgres -n psd-cloud` |
| NATS connection timeout | Verify NATS is running: `kubectl get pods -l app=nats -n psd-cloud` |
| Images not found (Minikube) | Run `eval $(minikube docker-env)` before building |
| Helm dependency errors | Run `helm dependency update infra/helm/` |
