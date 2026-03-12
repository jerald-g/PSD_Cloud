# PSD Cloud Security Platform

A cloud-native, multi-tenant security scanning and compliance platform built on microservices, Kubernetes, and event-driven architecture.

## Overview

PSD Cloud automates SAST (Static Application Security Testing) and DAST (Dynamic Application Security Testing) for any project, maps findings to **OWASP Top 10 2021** and **CIS Controls v8**, computes compliance scores, and delivers rich HTML + JSON reports through a live web dashboard.

## Architecture

8 microservices orchestrated on Kubernetes:

| Service | Role |
|---|---|
| api-gateway | JWT auth, request routing |
| auth-service | User registration, login, JWT issuance |
| scan-orchestrator | Scan lifecycle management, NATS job publishing |
| sast-scanner | Semgrep-based static analysis worker |
| dast-scanner | OWASP ZAP dynamic analysis worker |
| compliance-engine | OWASP/CIS mapping, compliance score computation |
| report-generator | Jinja2 HTML + JSON reports, MinIO storage |
| dashboard | React SPA – scan management and report viewer |

## Quick Start (Local Development)

```bash
# Prerequisites: Docker, Docker Compose

docker-compose -f docker-compose.dev.yml up --build

# Access:
# Dashboard:      http://localhost:3000
# API Gateway:    http://localhost:8080
# MinIO Console:  http://localhost:9001  (minioadmin / minioadmin123)
# Grafana:        http://localhost:3001  (admin / admin)
```

### Test Targets for Scanning

Three intentionally vulnerable .NET APIs are included for DAST testing:

| Target | URL | Description |
|---|---|---|
| VulnerableAPI | http://localhost:5000 | Full .NET Web API with common vulnerabilities |
| VulnerableMVC | http://localhost:5001 | .NET MVC app with security flaws |
| VulnerableMinimalAPI | http://localhost:5002 | .NET Minimal API with injection weaknesses |

Use these as DAST scan targets from the dashboard (e.g. `http://host.docker.internal:5000` when scanning from within Docker).

## Kubernetes Deployment

See the full [Kubernetes Deployment Guide](docs/deployment-guide.md) for detailed instructions.

```bash
# Deploy raw manifests to a local cluster (Docker Desktop / Minikube / k3s)
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/backing-services.yaml
kubectl apply -f kubernetes/microservices.yaml
kubectl apply -f kubernetes/ingress.yaml
```

## Documentation

- [System Architecture Overview](docs/architecture/system-overview.md)
- [Scan Lifecycle Data Flow](docs/architecture/data-flow.md)
- [Technical Report](docs/report/technical-report.md)

## Technology Stack

Kubernetes · FastAPI · React · NATS JetStream · PostgreSQL · Redis · MinIO · Semgrep · OWASP ZAP · Prometheus · Grafana
