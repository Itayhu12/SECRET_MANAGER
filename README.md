# Secure Secrets Manager

A small-scale secrets manager built with Flask. Stores encrypted API keys and credentials, supports one-time expiring share links, and enforces per-user access control.

---

## Quick start (VS Code + Windows)

### 1. Create the virtual environment

Open the project folder in VS Code, then open a terminal (`Ctrl + `` ` ``):

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

VS Code will prompt "We noticed a new virtual environment was created. Do you want to select it?" — click **Yes** to use `.venv` as the Python interpreter.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

```bash
# Copy the example file
cp .env.example .env
```

Now edit `.env` and fill in the three generated secrets:

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Generate JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Generate ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Paste each value into `.env`.

### 4. Run the app

```bash
flask run
```

Visit `http://127.0.0.1:5000/health` — you should see `{"status": "ok"}`.

---

## Project structure

```
secrets_manager/
├── app.py                  # Application factory
├── config.py               # Dev / prod / test config
├── requirements.txt
├── .env.example            # Template — copy to .env
├── .gitignore
│
├── routes/                 # HTTP layer (thin — delegate to services)
│   ├── auth.py             # POST /register, POST /login
│   ├── secrets.py          # CRUD /secrets
│   └── shares.py           # POST /secrets/<id>/share, GET /share/<token>
│
├── services/               # Business logic
│   ├── auth_service.py     # Password hashing, JWT
│   ├── crypto_service.py   # Fernet encrypt / decrypt
│   ├── secret_service.py   # Secret CRUD + ownership
│   └── share_service.py    # Token generation + consumption
│
├── models/                 # Data shapes (dataclasses)
│   ├── user.py
│   ├── secret.py
│   └── share.py
│
├── utils/                  # Cross-cutting helpers
│   ├── auth_middleware.py  # @require_auth decorator
│   ├── file_storage.py     # read_json / write_json
│   ├── audit_logger.py     # Append-only event log
│   └── validators.py       # Input validation
│
├── storage/                # File-based data (git-ignored except .gitkeep)
│   ├── users/
│   ├── secrets/
│   ├── shares/
│   └── audit/
│
├── tests/                  # pytest test suite
└── docs/
    └── api.md              # Endpoint reference
```

---

## Running tests

```bash
pytest tests/ -v
```

---

## Security notes

- `.env` is git-ignored — never commit it.
- All secret values are encrypted with Fernet before being written to disk.
- Plaintext values exist in memory only during encrypt/decrypt operations and are never logged.
- Share tokens are generated with `secrets.token_urlsafe(32)` — cryptographically random.
