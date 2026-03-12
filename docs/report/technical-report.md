# PSD Cloud Security Platform – Technical Report

---

## 1. Introduction

### 1.1 Project Background

This project is a cloud-native re-architecture submitted under **Option A – Extension of Team Project**. The original projects were:

1. **Security Compliance Engine** – A CI/CD template library that reduced YAML configuration overhead for SonarQube SAST + OWASP ZAP DAST pipelines. It operated as a shared Docker image consumed via GitLab CI templates and produced static HTML/JSON compliance reports.

2. **C# Security Scan** – An ASP.NET Core (.NET 8.0) web application containing intentional OWASP Top 10 vulnerabilities, used as a scan target to demonstrate the compliance engine's capabilities.

Both systems operated on a single Docker host, were single-tenant, required manual setup, and lacked cloud-native features such as event-driven processing, multi-tenancy, API-driven operation, cloud object storage, or production-grade observability.

### 1.2 Objectives

This project delivers a complete **cloud-native architectural redesign** that:
- Replaces the original Docker-only deployment with a Kubernetes microservices platform
- Introduces event-driven scan orchestration via NATS JetStream
- Adds multi-tenant user management with JWT authentication
- Provides a live React dashboard instead of static HTML outputs
- Adds production-grade observability (Prometheus + Grafana)

> **Compliance note:** No code, reports, diagrams, or text from the original projects has been reused. This is an independent architectural evolution.

---

## 2. System Architecture

### 2.1 Architecture Style

The platform uses a **microservices architecture** with **event-driven communication** between services. Key architectural decisions:

| Decision | Choice | Rationale |
|---|---|---|
| Deployment | Kubernetes | Cloud-agnostic, horizontal scaling, rolling updates |
| Service communication | NATS JetStream (async) + HTTP (sync) | Decouples scanners from orchestration; durable message delivery |
| SAST engine | Semgrep | Open-source, multi-language, OWASP Top 10 ruleset |
| DAST engine | OWASP ZAP | Industry standard, REST API control |
| Object storage | MinIO | S3-compatible; works locally and on any cloud |
| Auth | JWT (HS256) | Stateless, scales horizontally without session storage |
| Frontend | React + Vite | Fast SPA with live data from REST API |

### 2.2 Microservices

The platform consists of **eight microservices**:

1. **api-gateway** – Single entry point. Validates JWT tokens, proxies to downstream services, handles CORS.
2. **auth-service** – User registration, login, JWT issuance, token verification. PostgreSQL-backed.
3. **scan-orchestrator** – Accepts scan requests via REST, publishes jobs to NATS, tracks lifecycle state in PostgreSQL.
4. **sast-scanner** – Worker consuming `scan.sast.requested`; clones repo, runs Semgrep with OWASP rulesets, forwards findings.
5. **dast-scanner** – Worker consuming `scan.dast.requested`; drives ZAP spider + active scan, forwards alerts.
6. **compliance-engine** – Receives raw findings, maps to OWASP Top 10 2021 and CIS Controls v8, computes 0-100 compliance score.
7. **report-generator** – Renders Jinja2 HTML reports and JSON artefacts, uploads to MinIO.
8. **dashboard** – React SPA served via nginx; consumes API gateway for scan management, history, and report viewing.

### 2.3 Infrastructure

| Component | Technology | Purpose |
|---|---|---|
| PostgreSQL 16 | Relational DB | Users, scan records, findings summaries |
| Redis 7 | In-memory cache | Rate limiting, caching (future) |
| NATS JetStream | Message broker | Async scan job delivery, durable queues |
| MinIO | Object storage | HTML + JSON report files |
| Prometheus | Metrics collection | All services expose `/metrics` |
| Grafana | Metrics visualisation | Dashboards for scan throughput, latency |

---

## 3. Cloud-Native Design Principles

### 3.1 Twelve-Factor App

The platform follows Twelve-Factor principles:
- **Config** – All configuration via environment variables (no hardcoded credentials)
- **Backing services** – PostgreSQL, Redis, NATS, MinIO are attached resources; swap between local and managed cloud versions
- **Processes** – All services are stateless; horizontal scaling requires only replica count changes
- **Port binding** – Services export themselves via HTTP; no web server coupling
- **Logs** – All services log to stdout in structured format

### 3.2 Kubernetes Manifests

Deployment is declared in code via raw Kubernetes manifests for namespace, ingress, configmaps, and secrets, stored in the `kubernetes/` directory.

### 3.3 Observability

All Python services expose Prometheus metrics via `prometheus-fastapi-instrumentator`:
- Request rate, latency percentiles, error rate per endpoint
- SAST/DAST scan count and duration histograms
- Grafana provisioned with dashboards on startup

### 3.4 Security

- JWT authentication on all protected endpoints
- Non-root container execution (dedicated `appuser`)
- Secrets managed via Kubernetes Secrets (not embedded in images)
- TLS at the ingress layer via cert-manager (Let's Encrypt)

---

## 4. Scan Pipeline Design

### 4.1 SAST (Static Analysis)

Tool: **Semgrep** with the following rulesets:
- `p/owasp-top-ten` – Maps directly to OWASP Top 10 2021 categories
- `p/secrets` – Detects hardcoded credentials, API keys
- `p/ci` – CI/CD-specific security checks

The scanner clones the repository using `git clone --depth 1` (shallow clone for speed), runs Semgrep, and normalises findings to a common schema before forwarding to the compliance engine.

### 4.2 DAST (Dynamic Analysis)

Tool: **OWASP ZAP** controlled via its REST API:
1. Spider phase – crawls all accessible pages/endpoints
2. Active scan phase – tests for injection, XSS, SSRF, misconfiguration
3. Alert retrieval – collects all findings with severity, CWE, and solution guidance

### 4.3 Compliance Mapping

The compliance engine performs two levels of mapping:

**OWASP Top 10 2021 mapping:**
1. CWE ID direct match against OWASP category CWE lists
2. Keyword matching against category keywords in the finding text
3. Fallback to `UNKNOWN`

**CIS Controls v8 mapping:**
- Keyword matching against control-specific terms (e.g., "audit log" → CIS-8)

**Compliance Score:**
- Starts at 100
- Deducts: CRITICAL=10, HIGH=7, MEDIUM=4, LOW=1 per finding
- Capped at 0 (minimum)

### 4.4 Parallel Execution

SAST and DAST scans run **in parallel** via separate NATS subjects with dedicated durable consumer groups. Both workers independently forward results to the compliance engine. The compliance engine accumulates findings per scan and triggers report generation once all sub-scans complete.

---

## 5. Comparison: Original vs Cloud-Native Architecture

| Dimension | Original Projects | PSD Cloud (This Project) |
|---|---|---|
| Deployment target | Single Docker host | Kubernetes cluster (any cloud) |
| Tenancy | Single tenant | Multi-tenant (JWT user isolation) |
| Scan triggering | GitLab CI YAML template | REST API + webhook |
| Scanner control | Docker container startup | NATS event-driven workers |
| Results storage | CI artefact files | MinIO (cloud object storage) |
| Report delivery | Download from CI pipeline | Live dashboard + REST download |
| Compliance standards | OWASP Top 10 (basic) | OWASP Top 10 2021 + CIS Controls v8 |
| Observability | None | Prometheus + Grafana |
| Scaling | None (single container) | Horizontal pod autoscaling |

---

## 6. Deployment Guide

### 6.1 Local Development

```bash
# Prerequisites: Docker, Docker Compose

git clone https://gitlab.com/Gerald-codes1/psd-cloud
cd PSD_Cloud

docker-compose -f docker-compose.dev.yml up --build

# Services:
# API Gateway:      http://localhost:8080
# Dashboard:        http://localhost:3000
# MinIO Console:    http://localhost:9001  (minioadmin / minioadmin123)
# Grafana:          http://localhost:3001  (admin / admin)
# Prometheus:       http://localhost:9090
```

### 6.2 Kubernetes Deployment

```bash
# 1. Create namespace
kubectl apply -f kubernetes/namespace.yaml

# 2. Deploy backing services
kubectl apply -f kubernetes/backing-services.yaml

# 3. Deploy microservices
kubectl apply -f kubernetes/microservices.yaml

# 4. (Optional) Deploy ingress
kubectl apply -f kubernetes/ingress.yaml

# 5. Verify
kubectl get pods -n psd-cloud
```

### 6.3 API Usage

```bash
# Register a user
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret","full_name":"Test User"}'

# Login and get token
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/token \
  -d "username=user@example.com&password=secret" | jq -r .access_token)

# Start a full scan
curl -X POST http://localhost:8080/api/scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "my-app",
    "scan_type": "full",
    "repository_url": "https://github.com/example/my-app",
    "target_url": "https://my-app.example.com"
  }'

# Poll scan status
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/scans/<scan_id>
```

---

## 7. Future Work

- **RBAC** – Role-based access control for team/organisation isolation
- **Scheduled scans** – Cron-triggered recurring scans
- **Multi-scanner support** – Pluggable scanner registry (add Trivy, Checkov, Nuclei)
- **Dashboard alerts** – Real-time WebSocket updates on scan completion
- **SARIF export** – Industry-standard findings format for integration with GitHub/GitLab security tabs
- **SLA tracking** – Track remediation time for findings across scan cycles

---

## 8. References

- OWASP Top 10 2021: https://owasp.org/Top10/
- CIS Controls v8: https://www.cisecurity.org/controls/v8
- Semgrep documentation: https://semgrep.dev/docs/
- OWASP ZAP: https://www.zaproxy.org/
- NATS JetStream: https://docs.nats.io/nats-concepts/jetstream
- Kubernetes: https://kubernetes.io/docs/
