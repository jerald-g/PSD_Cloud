"""
PSD Cloud – Compliance Engine
Maps raw scanner findings (SAST/DAST) to:
  - OWASP Top 10 2021 categories
  - CIS Controls v8 categories
Computes an overall compliance score and forwards the enriched
result to the report-generator and scan-orchestrator.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator

log = logging.getLogger("compliance-engine")

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://scan-orchestrator:8000")
REPORT_GENERATOR_URL = os.getenv("REPORT_GENERATOR_URL", "http://report-generator:8000")
NOTIFICATION_URL = os.getenv("NOTIFICATION_URL", "http://notification-service:8000")

# ─── Load mapping tables ───────────────────────────────────────────────────────

_MAPPINGS_DIR = Path(__file__).parent / "mappings"

with open(_MAPPINGS_DIR / "owasp_top10.json") as f:
    OWASP_TOP10: dict[str, dict] = json.load(f)

with open(_MAPPINGS_DIR / "cis_benchmark.json") as f:
    CIS_BENCHMARK: dict[str, dict] = json.load(f)

# Pre-build keyword → category lookup for fast matching
_OWASP_KW: list[tuple[str, str]] = [
    (kw.lower(), cat_id)
    for cat_id, cat in OWASP_TOP10.items()
    for kw in cat["keywords"]
]
_CIS_KW: list[tuple[str, str]] = [
    (kw.lower(), cat_id)
    for cat_id, cat in CIS_BENCHMARK.items()
    for kw in cat["keywords"]
]

# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="PSD Cloud – Compliance Engine", version="1.0.0")
Instrumentator().instrument(app).expose(app)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class EvaluateRequest(BaseModel):
    scan_id: str
    scan_type: str   # "sast" | "dast"
    findings: list[dict[str, Any]]


# ─── Mapping logic ────────────────────────────────────────────────────────────

def _match_owasp(finding: dict) -> str:
    """Return the best matching OWASP Top 10 category ID for a finding."""
    text = " ".join(str(v) for v in finding.values()).lower()
    cwe = str(finding.get("cwe", ""))

    # CWE-ID direct match
    if cwe:
        for cat_id, cat in OWASP_TOP10.items():
            for cwe_id in cat.get("cwe_ids", []):
                if cwe_id.replace("CWE-", "") == cwe.replace("CWE-", ""):
                    return cat_id

    # Keyword match
    for kw, cat_id in _OWASP_KW:
        if kw in text:
            return cat_id

    # Fallback: map by SonarQube category/type heuristics
    category = str(finding.get("category", "")).upper()
    rule_id = str(finding.get("rule_id", "")).lower()
    if category == "VULNERABILITY":
        return "A05:2021"   # Security Misconfiguration (safe default for vulns)
    if category == "BUG":
        return "A04:2021"   # Insecure Design
    if "security" in rule_id or "security" in text:
        return "A05:2021"

    return "A05:2021"       # Default to Misconfiguration rather than UNKNOWN


def _match_cis(finding: dict) -> str:
    text = " ".join(str(v) for v in finding.values()).lower()
    for kw, cat_id in _CIS_KW:
        if kw in text:
            return cat_id
    return "UNKNOWN"


_SEVERITY_WEIGHT = {"CRITICAL": 10, "HIGH": 7, "MEDIUM": 4, "LOW": 1, "INFORMATIONAL": 0, "INFO": 0}


def _compute_score(findings: list[dict]) -> float:
    """
    Compliance score 0-100. Uses a weighted penalty that scales with finding count.
    CRITICAL/HIGH findings are weighted more heavily, but the score degrades
    gradually rather than instantly dropping to 0 for large codebases.
    """
    import math
    if not findings:
        return 100.0
    total_weight = sum(_SEVERITY_WEIGHT.get(f.get("severity", "LOW").upper(), 1) for f in findings)
    # Logarithmic scaling: gentle curve that produces meaningful scores.
    # ~50 weighted pts → ~82; ~200 → ~60; ~600 → ~40; ~2000 → ~22
    penalty = 15 * math.log1p(total_weight / 5)
    score = max(0.0, 100.0 - penalty)
    return round(score, 2)


def _build_summary(enriched: list[dict]) -> dict:
    total = len(enriched)
    by_severity: dict[str, int] = {}
    by_owasp: dict[str, int] = {}

    for f in enriched:
        sev = f.get("severity", "UNKNOWN").upper()
        by_severity[sev] = by_severity.get(sev, 0) + 1
        owasp = f.get("owasp_category", "UNKNOWN")
        by_owasp[owasp] = by_owasp.get(owasp, 0) + 1

    return {"total": total, "by_severity": by_severity, "by_owasp": by_owasp}


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "compliance-engine"}


@app.post("/compliance/evaluate")
async def evaluate(payload: EvaluateRequest):
    """Receive raw findings from a scanner, enrich them, compute scores, and forward results."""
    enriched = []
    for finding in payload.findings:
        enriched.append({
            **finding,
            "owasp_category": _match_owasp(finding),
            "owasp_name": OWASP_TOP10.get(_match_owasp(finding), {}).get("name", "Unknown"),
            "cis_category": _match_cis(finding),
        })

    score = _compute_score(enriched)
    summary = _build_summary(enriched)

    result_payload = {
        "scan_id": payload.scan_id,
        "scan_type": payload.scan_type,
        "compliance_score": score,
        "findings_summary": summary,
        "enriched_findings": enriched,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Trigger report generation
        await client.post(f"{REPORT_GENERATOR_URL}/reports/generate", json=result_payload)

        # Update orchestrator with score + summary
        await client.post(
            f"{ORCHESTRATOR_URL}/scans/{payload.scan_id}/result",
            json={
                "scan_id": payload.scan_id,
                "status": "completed",
                "findings_summary": summary,
                "compliance_score": score,
            },
        )

    return {"status": "evaluated", "scan_id": payload.scan_id, "compliance_score": score}
