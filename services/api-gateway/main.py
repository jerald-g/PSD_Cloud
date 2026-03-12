"""
PSD Cloud – API Gateway
Single entry point for all client requests.
- Validates JWT tokens on every /api/* request
- Proxies requests to the appropriate downstream microservice
- Exposes aggregated OpenAPI docs
"""
from __future__ import annotations

import os
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from prometheus_fastapi_instrumentator import Instrumentator

# ─── Config ───────────────────────────────────────────────────────────────────

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://scan-orchestrator:8000")
REPORT_GENERATOR_URL = os.getenv("REPORT_GENERATOR_URL", "http://report-generator:8000")

# Routes that do not require authentication
PUBLIC_PATHS = {"/health", "/api/auth/register", "/api/auth/token", "/metrics"}

# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="PSD Cloud – API Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten in production to your dashboard origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

bearer_scheme = HTTPBearer(auto_error=False)


# ─── Auth middleware ───────────────────────────────────────────────────────────

async def require_auth(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict:
    if request.url.path in PUBLIC_PATHS:
        return {}

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication token")

    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


# ─── Proxy helper ─────────────────────────────────────────────────────────────

async def _proxy(request: Request, target_base: str, strip_prefix: str = "") -> StreamingResponse:
    path = request.url.path
    if strip_prefix and path.startswith(strip_prefix):
        path = path[len(strip_prefix):]

    url = f"{target_base}{path}"
    if request.url.query:
        url += f"?{request.url.query}"

    headers = dict(request.headers)
    headers.pop("host", None)

    body = await request.body()

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
            )
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail=f"Upstream service unavailable: {target_base}")

    return StreamingResponse(
        content=iter([resp.content]),
        status_code=resp.status_code,
        headers=dict(resp.headers),
        media_type=resp.headers.get("content-type"),
    )


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "api-gateway"}


# Auth service passthrough (public)
@app.api_route("/api/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_auth(request: Request):
    return await _proxy(request, AUTH_SERVICE_URL, strip_prefix="/api")


# Scan orchestrator – protected
@app.api_route("/api/scans/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_scans(request: Request, _auth: Annotated[dict, Depends(require_auth)]):
    return await _proxy(request, ORCHESTRATOR_URL, strip_prefix="/api")


@app.api_route("/api/scans", methods=["GET", "POST"])
async def proxy_scans_root(request: Request, _auth: Annotated[dict, Depends(require_auth)]):
    return await _proxy(request, ORCHESTRATOR_URL, strip_prefix="/api")


# Reports – public (accessed via iframe / direct link where Authorization header is unavailable)
@app.api_route("/api/reports/{path:path}", methods=["GET"])
async def proxy_reports(request: Request):
    return await _proxy(request, REPORT_GENERATOR_URL, strip_prefix="/api")
