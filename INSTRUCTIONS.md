# PSD Cloud Security Platform - Setup & Running Instructions

## Prerequisites

Before running, make sure you have installed:

- **Docker Desktop** (v4.25+) with Docker Compose v2
  - Windows: https://docs.docker.com/desktop/install/windows-install/
  - Allocate at least **8 GB RAM** and **4 CPUs** to Docker (Settings > Resources)
- **Git** (for cloning the repo)
- **Node.js 20+** (only if you want to develop the dashboard outside Docker)
- **Python 3.12+** (only if you want to develop backend services outside Docker)

## Project Structure

```
PSD_Cloud/
  services/                    # 9 microservices
    api-gateway/               # JWT auth, request routing (FastAPI)
    auth-service/              # User registration & login (FastAPI + PostgreSQL)
    scan-orchestrator/         # Scan lifecycle management (FastAPI + NATS + Redis)
    sast-scanner/              # Static analysis worker (SonarQube integration)
    dast-scanner/              # Dynamic analysis worker (OWASP ZAP integration)
    compliance-engine/         # OWASP/CIS compliance mapping (FastAPI)
    report-generator/          # HTML/JSON report generation (FastAPI + MinIO)
    notification-service/      # Webhook notifications (FastAPI)
    dashboard/                 # Web UI (React + Vite)
  test-targets/                # Intentionally vulnerable .NET apps for testing
  kubernetes/                  # Raw K8s manifests
  infra/
    helm/                      # Helm chart for production deployment
    terraform/                 # Multi-cloud infrastructure provisioning
    observability/             # Prometheus + Grafana configs
  docker-compose.dev.yml       # Local development stack
```

## Step 1: Clone and Navigate

```bash
git clone <your-repo-url>
cd PSD_Cloud
```

## Step 2: Start the Platform (Docker Compose)

This is the primary way to run everything locally. One command starts all 9 microservices plus backing infrastructure (PostgreSQL, Redis, NATS, MinIO, SonarQube, ZAP, Prometheus, Grafana).

```bash
docker-compose -f docker-compose.dev.yml up --build
```

First run will take 5-10 minutes to pull images and build containers.

To run in the background (detached mode):

```bash
docker-compose -f docker-compose.dev.yml up --build -d
```

## Step 3: Access the Platform

Once all containers are healthy, access these URLs in your browser:

| Service | URL | Credentials |
|---|---|---|
| Dashboard (Web UI) | http://localhost:3000 | Register a new account |
| API Gateway | http://localhost:8085 | JWT token required |
| SonarQube | http://localhost:9100 | admin / admin |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin123 |
| Grafana | http://localhost:3001 | admin / admin |
| Prometheus | http://localhost:9090 | None |
| NATS Monitoring | http://localhost:8222 | None |

## Step 4: Create an Account & Run Your First Scan

### 4a. Register a user

```bash
curl -X POST http://localhost:8085/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "SecurePass123!", "full_name": "Test User"}'
```

### 4b. Login to get a JWT token

```bash
curl -X POST http://localhost:8085/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "SecurePass123!"}'
```

Save the returned `access_token` value.

### 4c. Create a scan

```bash
curl -X POST http://localhost:8085/api/scans \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -d '{
    "project_name": "test-project",
    "scan_type": "sast",
    "repository_url": "https://github.com/juice-shop/juice-shop.git"
  }'
```

### 4d. Check scan status

```bash
curl http://localhost:8085/api/scans \
  -H "Authorization: Bearer <YOUR_TOKEN>"
```

Or use the Dashboard at http://localhost:3000 to monitor scans visually.

## Step 5: Run the Test Targets (Optional)

The project includes intentionally vulnerable .NET applications for testing SAST/DAST scanning:

```bash
cd test-targets
docker-compose up --build
```

This starts three vulnerable apps:
- **VulnerableAPI** - REST API with SQL injection, XSS, IDOR flaws
- **VulnerableMinimalAPI** - Minimal API with security issues
- **VulnerableMVC** - MVC app with stored XSS, CSRF bypass

Use these as scan targets to test the platform's detection capabilities.

### Secrets in Test Targets

The test targets contain **intentionally hardcoded secrets** as part of their vulnerability demonstrations (OWASP A02/A05). All values are clearly fake and use `EXAMPLE`/`FAKE`/`DEMO` markers to avoid triggering GitHub Push Protection or secret scanners. These include fake Stripe keys (`sk_test_EXAMPLE_...`), AWS example credentials, and placeholder passwords.

> **Do not replace these with real secrets.** They exist to validate that the platform's SAST/DAST scanners correctly detect hardcoded credentials.

The **platform services** (auth-service, api-gateway, etc.) handle secrets correctly via environment variables in `docker-compose.dev.yml`. 

## Checking Service Health

Every service exposes a `/health` endpoint:

```bash
# API Gateway
curl http://localhost:8085/health

# Auth Service
curl http://localhost:8001/health

# Scan Orchestrator
curl http://localhost:8002/health
```

## Viewing Logs

```bash
# All services
docker-compose -f docker-compose.dev.yml logs -f

# Specific service
docker-compose -f docker-compose.dev.yml logs -f auth-service
docker-compose -f docker-compose.dev.yml logs -f scan-orchestrator
docker-compose -f docker-compose.dev.yml logs -f sast-scanner
```

## Stopping the Platform

```bash
# Stop all containers
docker-compose -f docker-compose.dev.yml down

# Stop and remove all data volumes (clean slate)
docker-compose -f docker-compose.dev.yml down -v
```

## Rebuilding After Code Changes

```bash
# Rebuild a specific service
docker-compose -f docker-compose.dev.yml up --build auth-service

# Rebuild everything
docker-compose -f docker-compose.dev.yml up --build
```

## Direct Service Ports (for API testing)

If you need to hit individual services directly (bypassing the API gateway):

| Service | Direct Port |
|---|---|
| auth-service | http://localhost:8001 |
| scan-orchestrator | http://localhost:8002 |
| PostgreSQL | localhost:5432 (user: psd, password: psd_secret, db: psd_cloud) |
| Redis | localhost:6379 |
| NATS | localhost:4222 |
| MinIO API | localhost:9000 |

## SonarQube Setup (for SAST scanning)

SonarQube needs a one-time setup after first boot:

1. Open http://localhost:9100
2. Login with `admin` / `admin` (you'll be asked to change the password)
3. Go to **My Account > Security > Generate Token**
4. Copy the token
5. Stop the platform and update `docker-compose.dev.yml`:
   - Set `SONARQUBE_TOKEN` in the `sast-scanner` service to your token
6. Restart: `docker-compose -f docker-compose.dev.yml up --build sast-scanner`

## Event Flow (How a Scan Works)

```
1. User creates scan via Dashboard or API
2. API Gateway authenticates and forwards to Scan Orchestrator
3. Scan Orchestrator saves to PostgreSQL, publishes job to NATS
4. SAST Scanner or DAST Scanner picks up the job
   - SAST: runs SonarQube analysis
   - DAST: runs OWASP ZAP spider + active scan
5. Scanner publishes results back to NATS
6. Compliance Engine maps findings to OWASP Top 10 / CIS Controls
7. Report Generator creates HTML + JSON report, stores in MinIO
8. Notification Service sends webhook notification
9. Dashboard polls for updates and displays results
```

## Troubleshooting

| Problem | Solution |
|---|---|
| Containers won't start | Check Docker Desktop is running and has enough resources (8GB+ RAM) |
| `port already in use` | Stop other services using that port, or change ports in docker-compose.dev.yml |
| PostgreSQL connection refused | Wait 30s after startup for health check to pass |
| SonarQube won't start | Increase Docker memory to 8GB+. SonarQube needs ~2GB alone |
| Dashboard shows blank page | Wait for api-gateway to be healthy first, then refresh |
| SAST scans fail | Check SonarQube is running and token is configured |
| DAST scans fail | Check ZAP container is running: `docker-compose -f docker-compose.dev.yml logs zap` |
| `no space left on device` | Run `docker system prune -a` to clean up old images |

## Kubernetes Deployment

There are two ways to deploy on Kubernetes: raw manifests (simplest) or Helm (production-ready).

### Option A: Raw Manifests (Docker Desktop / Minikube)

**Prerequisites:**
- Docker Desktop with **Kubernetes enabled** (Settings > Kubernetes > Enable Kubernetes), or Minikube installed
- `kubectl` installed and configured

**Step 1: Build Docker images locally**

```bash
# If using Docker Desktop Kubernetes, images are shared automatically.
# If using Minikube, first run: eval $(minikube docker-env)

# Build all 9 service images
for svc in auth-service scan-orchestrator sast-scanner dast-scanner \
           compliance-engine report-generator notification-service \
           api-gateway dashboard; do
  docker build -t psd-cloud/$svc:latest services/$svc/
done
```

**Step 2: Deploy using the script (easiest)**

```bash
bash kubernetes/deploy-local.sh
```

This script builds all images, creates the namespace, deploys backing services, waits for them to be ready, then deploys all microservices.

**Step 2 (alternative): Deploy manually step-by-step**

```bash
# Create the namespace
kubectl apply -f kubernetes/namespace.yaml

# Deploy backing services (PostgreSQL, Redis, NATS, MinIO, SonarQube, ZAP)
kubectl apply -f kubernetes/backing-services.yaml

# Wait for databases to be ready
kubectl wait --namespace psd-cloud --for=condition=ready pod -l app=postgres --timeout=120s
kubectl wait --namespace psd-cloud --for=condition=ready pod -l app=redis --timeout=60s
kubectl wait --namespace psd-cloud --for=condition=ready pod -l app=nats --timeout=60s

# Deploy the 9 microservices
kubectl apply -f kubernetes/microservices.yaml

# (Optional) Deploy ingress for domain-based routing
kubectl apply -f kubernetes/ingress.yaml
```

**Step 3: Check pod status**

```bash
kubectl get pods -n psd-cloud
```

Wait until all pods show `Running` status (1-3 minutes).

**Step 4: Access the services**

The raw manifests expose services via NodePort:

| Service | URL |
|---|---|
| Dashboard | http://localhost:30000 |
| API Gateway | http://localhost:30080 |
| SonarQube | http://localhost:30900 |
| MinIO Console | http://localhost:30901 |

If using Minikube, replace `localhost` with the output of `minikube ip`.

**Step 5: Tear down**

```bash
kubectl delete namespace psd-cloud
```

### Option B: Helm Chart (Production / Cloud Clusters)

**Prerequisites:**
- `helm` v3.12+ installed
- A Kubernetes cluster (EKS, AKS, GKE, or local)
- A container registry to push images to

**Step 1: Build and push images to your registry**

```bash
export REGISTRY=your-registry.example.com/psd-cloud
export TAG=$(git rev-parse --short HEAD)

for svc in auth-service scan-orchestrator sast-scanner dast-scanner \
           compliance-engine report-generator notification-service \
           api-gateway dashboard; do
  docker build -t $REGISTRY/$svc:$TAG services/$svc/
  docker push $REGISTRY/$svc:$TAG
done
```

**Step 2: Install Helm dependencies**

```bash
cd infra/helm
helm dependency update
```

This pulls the PostgreSQL, Redis, NATS, MinIO, and Prometheus sub-charts.

**Step 3: Deploy**

```bash
helm upgrade --install psd-cloud . \
  --namespace psd-cloud \
  --create-namespace \
  --set global.imageRegistry=$REGISTRY \
  --set global.imageTag=$TAG \
  --set global.jwtSecret=$(openssl rand -base64 32) \
  --set postgresql.auth.password=$(openssl rand -base64 16) \
  --set minio.auth.rootPassword=$(openssl rand -base64 16)
```

**Step 4: Verify**

```bash
kubectl get pods -n psd-cloud
kubectl get svc -n psd-cloud
```

**Step 5: Access via port-forward**

```bash
# Dashboard
kubectl port-forward svc/psd-cloud-dashboard 3000:80 -n psd-cloud

# API Gateway
kubectl port-forward svc/psd-cloud-api-gateway 8080:8000 -n psd-cloud

# Grafana (monitoring)
kubectl port-forward svc/psd-cloud-grafana 3001:80 -n psd-cloud
```

**Step 6: Tear down**

```bash
helm uninstall psd-cloud -n psd-cloud
kubectl delete namespace psd-cloud
```

### Kubernetes Troubleshooting

| Problem | Solution |
|---|---|
| Pods stuck in `Pending` | Not enough cluster resources. Check: `kubectl describe pod <name> -n psd-cloud` |
| Pods in `CrashLoopBackOff` | Check logs: `kubectl logs <pod-name> -n psd-cloud` |
| Pods in `ImagePullBackOff` | Images not built locally. Rebuild with `docker build` or check registry |
| Database connection refused | PostgreSQL pod not ready yet. Wait or check: `kubectl get pods -l app=postgres -n psd-cloud` |
| Helm dependency errors | Run `helm dependency update infra/helm/` |
| `NodePort` not accessible | On Docker Desktop, use `localhost`. On Minikube, use `minikube ip` |
