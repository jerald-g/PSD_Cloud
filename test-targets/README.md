# Test Targets – Intentionally Vulnerable C# Applications

These projects contain **intentional security vulnerabilities** for testing the PSD Cloud scanning platform. They should **never** be deployed to production.

## Projects

### 1. VulnerableAPI (ASP.NET Core Web API)
Port: `5000` | Swagger: `http://localhost:5000/swagger`

A REST API with comprehensive OWASP Top 10 vulnerabilities:

| OWASP Category | Vulnerability | Endpoint |
|---|---|---|
| A01: Broken Access Control | No authentication, IDOR, path traversal | `GET /api/users`, `GET /api/file/read?path=` |
| A02: Cryptographic Failures | Plain-text passwords, DES/MD5/SHA1, hardcoded secrets | `POST /api/admin/encrypt`, `GET /api/users/{id}` |
| A03: Injection | SQL injection, OS command injection | `POST /api/auth/login`, `GET /api/file/info?filename=` |
| A04: Insecure Design | Unrestricted file upload, no input validation, mass assignment | `POST /api/file/upload`, `PUT /api/users/{id}` |
| A05: Security Misconfiguration | Debug endpoints, CORS *, verbose errors, Swagger in prod | `GET /api/admin/debug` |
| A07: Auth Failures | No brute-force protection, static tokens, plain-text passwords | `POST /api/auth/login` |
| A08: Integrity Failures | XXE, insecure deserialization (BinaryFormatter) | `POST /api/admin/import-xml`, `POST /api/admin/deserialize` |
| A09: Logging Failures | Passwords and credit cards logged | `POST /api/auth/login` |
| A10: SSRF | Unrestricted URL fetching | `GET /api/admin/fetch?url=` |

### 2. VulnerableMVC (ASP.NET Core MVC)
Port: `5001`

A blog application with XSS, CSRF, and session vulnerabilities:

| OWASP Category | Vulnerability | Location |
|---|---|---|
| A03: Injection | Reflected XSS (search), Stored XSS (comments/bio), SQL injection | `/Home/Search`, `/Home/AddComment`, `/Profile/Create` |
| A05: Misconfiguration | No security headers (CSP, X-Frame-Options), no HTTPS | All pages |
| A07: Auth Failures | Insecure session cookies (HttpOnly=false, Secure=None) | Session config |
| A10: SSRF / Open Redirect | Unvalidated redirect URL | `/Home/Redirect?url=` |

### 3. VulnerableMinimalAPI (ASP.NET Core Minimal API)
Port: `5002` | Swagger: `http://localhost:5002/swagger`

An eCommerce-style API with financial and data security flaws:

| OWASP Category | Vulnerability | Endpoint |
|---|---|---|
| A01: Broken Access Control | No auth on any endpoint, negative transfers | `GET /api/customers`, `POST /api/transfer` |
| A02: Cryptographic Failures | MD5 hashing, hardcoded AWS keys/DB passwords | `POST /api/hash`, `GET /api/config` |
| A03: Injection | SQL injection, OS command injection | `GET /api/items/search?q=`, `GET /api/ping?host=` |
| A08: Integrity Failures | XXE processing | `POST /api/parse-xml` |
| A09: Logging Failures | Credit card + CVV logged | `POST /api/checkout` |
| A10: SSRF | Server-side URL proxy | `GET /api/proxy?url=` |

## Running

```bash
# Start all targets + SonarQube + ZAP
docker-compose -f test-targets/docker-compose.yml up --build

# Access:
# VulnerableAPI:        http://localhost:5000/swagger
# VulnerableMVC:        http://localhost:5001
# VulnerableMinimalAPI: http://localhost:5002/swagger
# SonarQube:            http://localhost:9000  (admin / admin)
# ZAP API:              http://localhost:8090

# Run SAST scan with SonarQube (example for VulnerableAPI):
dotnet tool install --global dotnet-sonarscanner
dotnet sonarscanner begin /k:"VulnerableAPI" /d:sonar.host.url=http://localhost:9000
dotnet build test-targets/VulnerableAPI/
dotnet sonarscanner end

# Run DAST scan with ZAP (example for VulnerableAPI):
curl "http://localhost:8090/JSON/spider/action/scan/?url=http://vulnerable-api:5000"
# Wait for spider to complete...
curl "http://localhost:8090/JSON/ascan/action/scan/?url=http://vulnerable-api:5000"
# Retrieve alerts:
curl "http://localhost:8090/JSON/alert/view/alerts/?baseurl=http://vulnerable-api:5000"
```
