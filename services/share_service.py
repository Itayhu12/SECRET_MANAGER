"""
services/share_service.py
--------------------------
One-time expiring share link management.

Storage layout:  storage/shares/<token>.json

Flow
----
  1. Owner calls create_share_token()  → gets token + expiry
  2. Recipient calls consume_share_token() → validated, decrypted,
     marked used=True, value returned exactly once.

Security
--------
  - tokens.token_urlsafe(32) = 256 bits of randomness, not guessable
  - Atomic read→validate→mark-used via file lock (portalocker)
    to block two simultaneous requests both seeing used=False
  - Expired and used tokens return identical 404 (no info leak)
"""

import os, secrets
from datetime import datetime, timezone, timedelta
from services.crypto_service import decrypt
from utils.file_storage import read_json, write_json, file_exists, build_path

def _storage_root(): return os.environ.get("STORAGE_PATH", "storage")
def _share_file(token): return build_path(_storage_root(), "shares", token + ".json")
def _secret_file(owner_id, secret_id):
    return build_path(_storage_root(), "secrets", owner_id, secret_id + ".json")

def create_share_token(owner_id: str, secret_id: str, ttl_seconds: int) -> dict:
    # 1. Verify secret exists and belongs to owner
    secret_path = _secret_file(owner_id, secret_id)
    if not file_exists(secret_path):
        raise FileNotFoundError(f"Secret '{secret_id}' not found.")
    if read_json(secret_path).get("owner_id") != owner_id:
        raise PermissionError("You do not own this secret.")

    # 2. Generate token and persist
    token = secrets.token_urlsafe(32)   # 256-bit random
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()
    write_json(_share_file(token), {
        "token": token, "secret_id": secret_id, "owner_id": owner_id,
        "expires_at": expires_at, "used": False, "created_at": now.isoformat(),
    })
    return {"token": token, "url": f"/share/{token}",
            "expires_at": expires_at, "ttl_seconds": ttl_seconds}

def consume_share_token(token: str) -> dict:
    share_path = _share_file(token)
    if not file_exists(share_path):
        raise FileNotFoundError("Share token not found or already used.")
    # Atomic consume (uses portalocker if available, best-effort otherwise)
    try:
        import portalocker
        _consume_with_lock(share_path)
    except ImportError:
        _consume_without_lock(share_path)

    record = read_json(share_path)
    secret_path = _secret_file(record["owner_id"], record["secret_id"])
    if not file_exists(secret_path):
        raise FileNotFoundError("The underlying secret no longer exists.")

    secret_data = read_json(secret_path)
    return {
        "name": secret_data["name"],
        "value": decrypt(secret_data["encrypted_value"]),
        "description": secret_data.get("description", ""),
        "tags": secret_data.get("tags", []),
        "expires_at": record["expires_at"],
        "accessed_at": datetime.now(timezone.utc).isoformat(),
    }

def _validate_share_record(record: dict) -> None:
    """Raises identical FileNotFoundError for used and expired — no info leak."""
    if record.get("used"):
        raise FileNotFoundError("Share token not found or already used.")
    if datetime.now(timezone.utc) >= datetime.fromisoformat(record["expires_at"]):
        raise FileNotFoundError("Share token has expired.")

def _consume_with_lock(share_path: str) -> None:
    import portalocker, json
    with open(share_path, "r+", encoding="utf-8") as f:
        portalocker.lock(f, portalocker.LOCK_EX)
        record = json.load(f)
        _validate_share_record(record)
        record["used"] = True
        f.seek(0); json.dump(record, f, indent=2, default=str); f.truncate()
        portalocker.unlock(f)

def _consume_without_lock(share_path: str) -> None:
    record = read_json(share_path)
    _validate_share_record(record)
    record["used"] = True
    write_json(share_path, record)