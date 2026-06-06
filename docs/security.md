# Security Design Decisions

This document explains the security choices made in each layer of the application.

---

## Encryption at rest

**Algorithm:** Fernet (AES-128-CBC + HMAC-SHA256, random IV per message)

Fernet was chosen over raw AES because it is an authenticated encryption scheme —
the HMAC means a tampered or corrupted ciphertext is detected and rejected at
decrypt time rather than silently returning garbage. Each call to `encrypt()`
produces a different ciphertext because a fresh 16-byte IV is generated per message.

**Key storage:** The `ENCRYPTION_KEY` lives only in the environment (`.env` file
or system environment). It is never written to disk as part of the application code.

**Plaintext lifetime:** The decrypted value exists in memory only long enough to
return it in an HTTP response. It is never written to a file, never logged,
and never included in list responses.

---

## Password hashing

**Algorithm:** bcrypt, work factor 12

bcrypt was chosen over SHA-family hashes because it is deliberately slow (making
brute-force attacks expensive) and includes a salt automatically. Work factor 12
means approximately 300 ms per hash on modern hardware — acceptable for a login
endpoint, significant cost for an attacker with a stolen database.

**Timing-safe login:** The `authenticate_user` function always runs `bcrypt.checkpw()`
even when the username does not exist, using a dummy hash. Without this, an attacker
could distinguish "wrong username" from "wrong password" by measuring response time.

---

## JWT authentication

**Algorithm:** HS256 (HMAC-SHA256) signed with `JWT_SECRET_KEY`

Tokens carry: `sub` (user_id), `username`, `iat` (issued at), `exp` (expiry).
The default TTL is 60 minutes. There is no refresh token mechanism — users
re-authenticate after expiry.

**Middleware:** The `@require_auth` decorator reads the `Authorization: Bearer`
header, decodes the JWT, and stores the payload in Flask's `g.current_user`.
Expired and malformed tokens both return `401` with distinct error codes so the
client can distinguish them.

---

## Access control

**Ownership model:** Every secret is stored at
`storage/secrets/{owner_id}/{secret_id}.json`. Ownership is enforced in two ways:

1. Directory isolation — a request for `secret_id` only looks inside the
   authenticated user's own directory.
2. Field check — `_load_and_verify()` also compares the `owner_id` field inside
   the file against the authenticated user's ID as a defence-in-depth measure.

Accessing another user's secret returns `403 FORBIDDEN`. The secret's existence
is therefore revealed to an authenticated user who guesses a valid UUID belonging
to someone else. If you prefer not to reveal existence, change both failure
branches in `_load_and_verify` to raise `FileNotFoundError`.

---

## Share tokens

**Generation:** `secrets.token_urlsafe(32)` produces 32 bytes (256 bits) of
cryptographic randomness encoded in URL-safe base64. At this length a brute-force
search is computationally infeasible.

**Validation order:** Every consume attempt checks:
1. Does the file exist? (token was issued)
2. Is `used == False`? (not already consumed)
3. Is `expires_at` in the future? (not expired)

All three failure cases return identical `404 TOKEN_INVALID` responses. This prevents
an attacker from learning whether a token existed, was already consumed, or expired.

**Atomic consume:** A file lock (`portalocker`) is held while the token record is
read, validated, and marked `used=True`. This prevents a race condition where two
simultaneous requests both read `used=False` and both succeed. Without the lock,
a determined attacker who fires two requests in parallel could redeem a one-time
token twice.

---

## Audit logging

**Format:** Newline-delimited JSON (`.jsonl`), append-only.

**What is logged:** Timestamp, event type, user_id, secret_id (never value),
token prefix (first 8 chars only), IP address.

**What is never logged:**
- Secret values (plaintext or ciphertext)
- Passwords or password hashes
- Full share tokens (only the first 8 chars are stored for correlation)

**Failure isolation:** Authentication failures are written to `_failures.jsonl`
rather than a user-specific file, because the user identity is not yet known
(the credentials may be wrong). Only a truncated username hint (≤20 chars) is
stored to support abuse detection without reconstructing the attempted credential.

---

## Rate limiting

Flask-Limiter with in-memory storage applies the following limits per client IP:

| Endpoint | Limit | Reason |
|----------|-------|--------|
| POST /register | 5 / min | Prevent mass account creation |
| POST /login | 10 / min | Slow down credential stuffing |
| Everything else | 50 / hr, 200 / day | General abuse prevention |
| GET /health | Unlimited | Monitoring probes must not be blocked |

---

## Input validation (OWASP alignment)

Every field is validated before it reaches business logic:

| Attack vector | Defence |
|---------------|---------|
| Null byte injection | `_check_null_bytes()` rejects `\x00` in all string inputs |
| Oversized payloads | Per-field length limits (name ≤255, value ≤10 000, etc.) |
| Non-string types | `isinstance(x, str)` check before any string operation |
| Path traversal | `build_path()` uses `os.path.normpath()` to collapse `../` |
| Malformed JSON | `request.get_json(silent=True) or {}` never raises on bad body |
| SQL injection | Not applicable — no SQL database used |

---

## File storage security

**Atomic writes:** `write_json()` writes to `<path>.tmp` then calls `os.replace()`.
On POSIX systems this is a single atomic `rename(2)` syscall — a crash or power
failure mid-write leaves the old file intact rather than a half-written one.

**Directory isolation:** User secrets live under `storage/secrets/{user_id}/`.
A directory listing of one user's folder never reveals another user's secret IDs.

**Git exclusions:** `.gitignore` excludes all runtime data under `storage/` except
the `.gitkeep` files that preserve the directory structure. The `.env` file is
also excluded. Neither secrets nor credentials should ever be committed.
