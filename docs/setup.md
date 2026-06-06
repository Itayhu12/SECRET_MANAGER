# Setup & Deployment Guide

## Requirements

| Tool | Minimum version |
|------|----------------|
| Python | 3.10+ |
| pip | 23+ |
| VS Code | Any recent version |

---

## Local development setup (VS Code / Windows)

### 1 — Clone or extract the project

```
secrets_manager/
├── app.py
├── config.py
├── requirements.txt
├── .env.example
├── routes/
├── services/
├── utils/
├── models/
├── storage/
├── tests/
└── docs/
```

### 2 — Create the virtual environment

Open the project folder in VS Code, then open the integrated terminal (`Ctrl + `` ` ``).

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

VS Code will show a popup: *"We noticed a new virtual environment. Select it as the workspace interpreter?"* — click **Yes**.

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### 4 — Generate secrets and configure the environment

```bash
# Copy the example file
cp .env.example .env      # Windows: copy .env.example .env
```

Now open `.env` and fill in the three generated values:

```bash
# Generate SECRET_KEY — paste into .env as SECRET_KEY=...
python -c "import secrets; print(secrets.token_hex(32))"

# Generate JWT_SECRET_KEY — paste into .env as JWT_SECRET_KEY=...
python -c "import secrets; print(secrets.token_hex(32))"

# Generate ENCRYPTION_KEY — paste into .env as ENCRYPTION_KEY=...
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Your `.env` should look like:
```
FLASK_ENV=development
FLASK_DEBUG=1
FLASK_APP=app.py
SECRET_KEY=9f3a...64 hex chars...
JWT_SECRET_KEY=1c7b...64 hex chars...
JWT_ACCESS_TOKEN_EXPIRES_MINUTES=60
ENCRYPTION_KEY=abc123...base64 fernet key...
STORAGE_PATH=storage
SHARE_DEFAULT_TTL_SECONDS=3600
SHARE_MAX_TTL_SECONDS=86400
```

> ⚠️ Never commit `.env` to version control. It is already in `.gitignore`.

### 5 — Run the development server

```bash
flask run
```

Visit `http://127.0.0.1:5000/health` — you should see:
```json
{ "status": "ok", "env": "development" }
```

### 6 — Run the test suite

```bash
pytest tests/ -v
```

All 61 tests should pass. Tests use an isolated `storage_test/` directory and are cleaned up automatically.

---

## Project structure explained

```
app.py                      Application factory — registers all blueprints
config.py                   Config classes (Dev / Prod / Test), reads from .env

routes/
  auth.py                   POST /register, POST /login
  secrets.py                CRUD /secrets/*
  shares.py                 POST /secrets/<id>/share, GET /share/<token>

services/
  auth_service.py           Password hashing (bcrypt), JWT issue/verify
  crypto_service.py         Fernet encrypt / decrypt
  secret_service.py         Secret CRUD + ownership enforcement
  share_service.py          Token generation + atomic one-time consume

utils/
  auth_middleware.py        @require_auth decorator (JWT → g.current_user)
  file_storage.py           ONLY place that calls open() — atomic writes
  audit_logger.py           Append-only .jsonl event log
  validators.py             Input cleaning + rejection (null bytes, sizes, etc.)

models/
  user.py                   User dataclass (id, username, password_hash)
  secret.py                 Secret dataclass (id, owner_id, encrypted_value, ...)
  share.py                  ShareToken dataclass (token, expires_at, used)

storage/                    File-based data — git-ignored at runtime
  users/                    One JSON file per user + index.json
  secrets/<user_id>/        One JSON file per secret, namespaced by owner
  shares/                   One JSON file per share token
  audit/                    One .jsonl file per user + _failures.jsonl

tests/
  test_health.py            Smoke test (app boots, /health responds)
  test_auth.py              Registration, login, JWT middleware — 12 tests
  test_secrets.py           Encrypt/decrypt CRUD, access control — 15 tests
  test_shares.py            Tokens, one-time use, expiry — 14 tests
  test_phase4.py            Audit log, rate limits, input hardening — 20 tests

docs/
  api.md                    Full endpoint reference with curl examples
  setup.md                  This file
  security.md               Security design decisions
```

---

## Key environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | Flask session signing key |
| `JWT_SECRET_KEY` | ✅ | JWT HMAC signing key |
| `ENCRYPTION_KEY` | ✅ | Fernet key for secret values at rest |
| `FLASK_ENV` | ✅ | `development` or `production` |
| `STORAGE_PATH` | ❌ | Root dir for file storage (default: `storage`) |
| `JWT_ACCESS_TOKEN_EXPIRES_MINUTES` | ❌ | Token TTL in minutes (default: `60`) |
| `SHARE_DEFAULT_TTL_SECONDS` | ❌ | Default share link lifetime (default: `3600`) |
| `SHARE_MAX_TTL_SECONDS` | ❌ | Max share link lifetime (default: `86400`) |

---

## Smoke-test walkthrough

The sequence below exercises every endpoint end-to-end.

```bash
# 0. Start the server
flask run

# 1. Register
curl -s -X POST http://127.0.0.1:5000/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "SecurePass1!"}'

# 2. Login — copy the access_token from the response
curl -s -X POST http://127.0.0.1:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "SecurePass1!"}'

# Set the token in your shell (paste your real token)
TOKEN="eyJhbGci..."

# 3. Store a secret
curl -s -X POST http://127.0.0.1:5000/secrets/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My API Key", "value": "sk_live_abc123", "tags": ["prod"]}'

# Copy the secret id from the response
SECRET_ID="x1y2z3-..."

# 4. List secrets (no values returned)
curl -s http://127.0.0.1:5000/secrets/ \
  -H "Authorization: Bearer $TOKEN"

# 5. Get the secret (value is decrypted and returned)
curl -s http://127.0.0.1:5000/secrets/$SECRET_ID \
  -H "Authorization: Bearer $TOKEN"

# 6. Update metadata
curl -s -X PUT http://127.0.0.1:5000/secrets/$SECRET_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Renamed Key", "tags": ["prod", "renamed"]}'

# 7. Create a share link (1 hour TTL)
curl -s -X POST http://127.0.0.1:5000/secrets/$SECRET_ID/share \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ttl_seconds": 3600}'

# Copy the token from the response
SHARE_TOKEN="aB3dEf8h..."

# 8. Access the share (no auth needed — works once only)
curl -s http://127.0.0.1:5000/share/$SHARE_TOKEN

# 9. Try again — must return 404 TOKEN_INVALID
curl -s http://127.0.0.1:5000/share/$SHARE_TOKEN

# 10. Delete the secret
curl -s -X DELETE http://127.0.0.1:5000/secrets/$SECRET_ID \
  -H "Authorization: Bearer $TOKEN"
```
