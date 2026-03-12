# Scan Lifecycle Data Flow

## Overview

This document describes the end-to-end data flow for a security scan from request submission through to report delivery.

---

## Sequence Diagram

```mermaid
sequenceDiagram
    actor User
    participant GW as API Gateway
    participant AUTH as Auth Service
    participant ORCH as Scan Orchestrator
    participant NATS as NATS JetStream
    participant SAST as SAST Scanner
    participant DAST as DAST Scanner
    participant CE as Compliance Engine
    participant RG as Report Generator
    participant MINIO as MinIO Storage
    participant DASH as Dashboard

    User->>GW: POST /api/auth/token (credentials)
    GW->>AUTH: Forward login request
    AUTH-->>GW: JWT access token
    GW-->>User: JWT token

    User->>GW: POST /api/scans (Bearer JWT)
    GW->>GW: Validate JWT
    GW->>ORCH: Forward scan request
    ORCH->>ORCH: Create Scan record (status=PENDING)
    ORCH->>NATS: Publish scan.sast.requested
    ORCH->>NATS: Publish scan.dast.requested
    ORCH->>ORCH: Update status=RUNNING
    ORCH-->>GW: Scan response (id, status=running)
    GW-->>User: 201 Created {scan_id}

    par SAST Worker
        NATS->>SAST: Deliver scan.sast.requested
        SAST->>SAST: git clone repository
        SAST->>SAST: semgrep scan (OWASP ruleset)
        SAST->>CE: POST /compliance/evaluate {findings}
    and DAST Worker
        NATS->>DAST: Deliver scan.dast.requested
        DAST->>DAST: ZAP Spider + Active Scan
        DAST->>CE: POST /compliance/evaluate {findings}
    end

    CE->>CE: Map findings → OWASP Top 10 + CIS
    CE->>CE: Compute compliance score
    CE->>RG: POST /reports/generate {enriched_findings}
    CE->>ORCH: POST /scans/{id}/result (score, summary)

    RG->>RG: Render HTML via Jinja2
    RG->>MINIO: PUT report.html + report.json
    RG->>ORCH: POST /scans/{id}/result (report_url)

    User->>DASH: View scan history
    DASH->>GW: GET /api/scans
    GW->>ORCH: Forward request
    ORCH-->>DASH: Scan list with scores

    User->>DASH: View report
    DASH->>GW: GET /api/reports/{id}/html
    GW->>RG: Forward
    RG->>MINIO: GET report.html
    MINIO-->>RG: Report bytes
    RG-->>DASH: HTML report
```

---

## Data Contracts

### Scan Job (NATS payload)
```json
{
  "scan_id": "uuid",
  "project_name": "string",
  "repository_url": "https://...",
  "target_url": "https://..."
}
```

### Finding (normalised – from any scanner)
```json
{
  "rule_id": "string",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
  "message": "string",
  "file": "optional path",
  "url": "optional URL",
  "line_start": 42,
  "cwe": "CWE-89",
  "source": "semgrep|zap",
  "owasp_category": "A03:2021",
  "owasp_name": "Injection",
  "cis_category": "CIS-16"
}
```

### Compliance Evaluation Result
```json
{
  "scan_id": "uuid",
  "compliance_score": 73.5,
  "findings_summary": {
    "total": 14,
    "by_severity": { "CRITICAL": 1, "HIGH": 3, "MEDIUM": 6, "LOW": 4 },
    "by_owasp": { "A03:2021": 5, "A07:2021": 3, "A05:2021": 4, "UNKNOWN": 2 }
  }
}
```
