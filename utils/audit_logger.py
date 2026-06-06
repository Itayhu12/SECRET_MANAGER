"""
utils/audit_logger.py
---------------------
Append-only structured audit log.
Storage: storage/audit/<user_id>.jsonl  (one JSON line per event)

Security rules:
  - Secret VALUES are NEVER written — IDs only
  - Files are append-only (mode "a") — never edited
  - Auth failures → _failures.jsonl (no user identity known yet)
  - Tokens: first 8 chars only — enough to correlate, not replay
"""

import json, os
from datetime import datetime, timezone
from utils.file_storage import build_path


def _audit_file(user_id: str) -> str:
    storage = os.environ.get("STORAGE_PATH", "storage")
    return build_path(storage, "audit", user_id + ".jsonl")


def log_event(event, user_id="anonymous", secret_id=None,
              token=None, ip_address=None, extra=None) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event":     event,
        "user_id":   user_id,
    }
    if secret_id:  entry["secret_id"]    = secret_id
    if token:      entry["token_prefix"] = token[:8] + "..."
    if ip_address: entry["ip_address"]   = ip_address
    if extra:
        safe = {k: v for k, v in extra.items()
                if not any(w in k.lower()
                           for w in ("value", "password", "secret", "key"))}
        entry.update(safe)
    _append(user_id, entry)


def log_auth_failure(username_hint: str, ip_address: str = None) -> None:
    hint = (username_hint or "")[:20]
    entry = {
        "timestamp":     datetime.now(timezone.utc).isoformat(),
        "event":         "auth.login_failed",
        "user_id":       "anonymous",
        "username_hint": hint + ("..." if len(username_hint or "") > 20 else ""),
        "ip_address":    ip_address or "unknown",
    }
    _append("_failures", entry)


def _append(user_id: str, entry: dict) -> None:
    path = _audit_file(user_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")