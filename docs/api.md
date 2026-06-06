# Secure Secrets Manager — API Reference

## Base URL
```
http://127.0.0.1:5000
```

## Authentication
All endpoints marked 🔒 require a JWT in the Authorization header:
```
Authorization: Bearer <access_token>
```
Tokens are issued by `POST /login` and expire after 60 minutes (configurable).

## Error envelope
Every error response uses this consistent shape:
```json
{ "error": "Human-readable message", "code": "MACHINE_READABLE_CODE" }
```

| HTTP | Code | Meaning |
|------|------|---------|
| 400 | VALIDATION_ERROR | Bad input — see error message |
| 400 | USERNAME_TAKEN | Registration duplicate |
| 401 | MISSING_TOKEN | No Authorization header |
| 401 | TOKEN_EXPIRED | JWT has expired — log in again |
| 401 | INVALID_TOKEN | JWT is malformed or wrong key |
| 401 | INVALID_CREDENTIALS | Wrong username or password |
| 403 | FORBIDDEN | Secret belongs to another user |
| 404 | NOT_FOUND | Secret or endpoint not found |
| 404 | TOKEN_INVALID | Share token missing, used, or expired |
| 429 | RATE_LIMIT_EXCEEDED | Too many requests — slow down |
| 500 | INTERNAL_ERROR | Unexpected server error |

---

## Auth endpoints

### POST /register
Create a new user account.

**Rate limit:** 5 requests / minute per IP

**Request body**
```json
{
  "username": "alice",
  "password": "s3cur3P@ss!"
}
```

| Field | Type | Rules |
|-------|------|-------|
| username | string | 3–50 chars, letters/digits/underscores only |
| password | string | 8–128 chars |

**Response 201**
```json
{
  "id": "a1b2c3d4-...",
  "username": "alice",
  "created_at": "2024-01-15T10:30:00+00:00"
}
```

**curl example**
```bash
curl -s -X POST http://127.0.0.1:5000/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "s3cur3P@ss!"}'
```

---

### POST /login
Authenticate and receive a JWT access token.

**Rate limit:** 10 requests / minute per IP

**Request body**
```json
{
  "username": "alice",
  "password": "s3cur3P@ss!"
}
```

**Response 200**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600,
  "user_id": "a1b2c3d4-...",
  "username": "alice"
}
```

**curl example**
```bash
curl -s -X POST http://127.0.0.1:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "s3cur3P@ss!"}'
```

---

## Secrets endpoints

### GET /secrets/ 🔒
List all secrets for the authenticated user. Returns metadata only — **never** the decrypted value.

**Response 200**
```json
[
  {
    "id": "x1y2z3-...",
    "owner_id": "a1b2c3d4-...",
    "name": "Stripe API Key",
    "description": "Production Stripe key",
    "tags": ["payments", "live"],
    "created_at": "2024-01-15T10:31:00+00:00",
    "updated_at": "2024-01-15T10:31:00+00:00"
  }
]
```
Returns `[]` if the user has no secrets.

**curl example**
```bash
curl -s http://127.0.0.1:5000/secrets/ \
  -H "Authorization: Bearer $TOKEN"
```

---

### POST /secrets/ 🔒
Store a new encrypted secret.

**Request body**
```json
{
  "name": "Stripe API Key",
  "value": "sk_live_abc123",
  "description": "Production Stripe key",
  "tags": ["payments", "live"]
}
```

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| name | string | ✅ | 1–255 chars |
| value | string | ✅ | 1–10 000 chars |
| description | string | ❌ | 0–1 000 chars |
| tags | list[string] | ❌ | max 10 tags, each max 50 chars |

**Response 201** — metadata only, no value in response
```json
{
  "id": "x1y2z3-...",
  "owner_id": "a1b2c3d4-...",
  "name": "Stripe API Key",
  "description": "Production Stripe key",
  "tags": ["payments", "live"],
  "created_at": "2024-01-15T10:31:00+00:00",
  "updated_at": "2024-01-15T10:31:00+00:00"
}
```

**curl example**
```bash
curl -s -X POST http://127.0.0.1:5000/secrets/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Stripe API Key", "value": "sk_live_abc123", "tags": ["payments"]}'
```

---

### GET /secrets/\<id\> 🔒
Retrieve and decrypt a secret. Only the owner can access it.

**Response 200** — includes decrypted `value`
```json
{
  "id": "x1y2z3-...",
  "owner_id": "a1b2c3d4-...",
  "name": "Stripe API Key",
  "description": "Production Stripe key",
  "tags": ["payments", "live"],
  "value": "sk_live_abc123",
  "created_at": "2024-01-15T10:31:00+00:00",
  "updated_at": "2024-01-15T10:31:00+00:00"
}
```

**curl example**
```bash
curl -s http://127.0.0.1:5000/secrets/x1y2z3-... \
  -H "Authorization: Bearer $TOKEN"
```

---

### PUT /secrets/\<id\> 🔒
Update secret metadata. Does **not** change the encrypted value.

**Request body** — all fields optional, at least one required
```json
{
  "name": "Stripe Live Key",
  "description": "Updated description",
  "tags": ["payments", "live", "updated"]
}
```

**Response 200** — updated metadata (no value)

**curl example**
```bash
curl -s -X PUT http://127.0.0.1:5000/secrets/x1y2z3-... \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Stripe Live Key", "tags": ["payments", "live"]}'
```

---

### DELETE /secrets/\<id\> 🔒
Permanently delete a secret. This action cannot be undone.

**Response 204** — no body

**curl example**
```bash
curl -s -X DELETE http://127.0.0.1:5000/secrets/x1y2z3-... \
  -H "Authorization: Bearer $TOKEN"
```

---

## Share endpoints

### POST /secrets/\<id\>/share 🔒
Generate a one-time expiring share link for a secret.
Only the secret's owner can create share links.
Multiple independent tokens can exist for the same secret simultaneously.

**Request body** — optional
```json
{
  "ttl_seconds": 3600
}
```

| Field | Type | Default | Rules |
|-------|------|---------|-------|
| ttl_seconds | integer | 3600 | 1–86 400 (24 h max) |

**Response 201**
```json
{
  "token": "aB3dEf8hIjKlMnOpQrStUvWxYz...",
  "url": "/share/aB3dEf8hIjKlMnOpQrStUvWxYz...",
  "expires_at": "2024-01-15T11:31:00+00:00",
  "ttl_seconds": 3600
}
```

**curl example**
```bash
curl -s -X POST http://127.0.0.1:5000/secrets/x1y2z3-.../share \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ttl_seconds": 3600}'
```

---

### GET /share/\<token\>
Access a shared secret via its one-time token. **No authentication required.**
The token is permanently invalidated after the first successful access.

**Response 200**
```json
{
  "name": "Stripe API Key",
  "value": "sk_live_abc123",
  "description": "Production Stripe key",
  "tags": ["payments", "live"],
  "expires_at": "2024-01-15T11:31:00+00:00",
  "accessed_at": "2024-01-15T10:45:00+00:00"
}
```

**Response 404** — token not found, already used, or expired
```json
{
  "error": "Share token not found, already used, or expired.",
  "code": "TOKEN_INVALID"
}
```
> Note: The response is identical for all three failure cases to prevent information leakage.

**curl example**
```bash
# First access — succeeds
curl -s http://127.0.0.1:5000/share/aB3dEf8h...

# Second access — returns 404
curl -s http://127.0.0.1:5000/share/aB3dEf8h...
```

---

## Health check

### GET /health
Liveness probe — no authentication required. Exempt from rate limiting.

**Response 200**
```json
{ "status": "ok", "env": "development" }
```

---

## Rate limits summary

| Endpoint | Limit |
|----------|-------|
| POST /register | 5 / minute per IP |
| POST /login | 10 / minute per IP |
| All other endpoints | 50 / hour, 200 / day per IP |
| GET /health | Unlimited |
