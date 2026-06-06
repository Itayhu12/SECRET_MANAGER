"""
services/auth_service.py
------------------------
All business logic for user registration, login, and JWT lifecycle.

Storage layout
--------------
  storage/users/<user_id>.json          — user record (hashed password)
  storage/users/index.json              — { username -> user_id } lookup map

Security notes
--------------
  - Passwords are hashed with bcrypt (work factor 12).
  - Plaintext passwords are never stored, logged, or returned.
  - JWTs are signed with HS256 using JWT_SECRET_KEY from the environment.
  - Token expiry defaults to 60 minutes (JWT_ACCESS_TOKEN_EXPIRES_MINUTES).
"""

import os
import uuid
from datetime import datetime, timezone, timedelta

import bcrypt
import jwt

from utils.file_storage import (
    read_json, write_json, file_exists, build_path
)


# ── Internal helpers ────────────────────────────────────────────────────────

def _get_storage_path() -> str:
    """Return the configured storage root (falls back to 'storage')."""
    return os.environ.get("STORAGE_PATH", "storage")


def _users_dir() -> str:
    return build_path(_get_storage_path(), "users")


def _user_file(user_id: str) -> str:
    return build_path(_users_dir(), user_id + ".json")


def _index_file() -> str:
    """username → user_id lookup index."""
    return build_path(_users_dir(), "index.json")


def _load_index() -> dict:
    """Load the username index; return {} if it doesn't exist yet."""
    path = _index_file()
    if not file_exists(path):
        return {}
    return read_json(path)


def _save_index(index: dict) -> None:
    write_json(_index_file(), index)


def _get_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET_KEY", "")
    if not secret:
        raise EnvironmentError("JWT_SECRET_KEY is not set.")
    return secret


def _token_ttl_minutes() -> int:
    return int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", 60))


# ── Public API ──────────────────────────────────────────────────────────────

def register_user(username: str, password: str) -> dict:
    """
    Create a new user account.

    Steps:
      1. Check the index — reject if username already taken.
      2. Hash the password with bcrypt (cost factor 12).
      3. Persist user record to storage/users/<id>.json.
      4. Add username → id mapping to the index.

    Returns the public user dict (no password hash).
    Raises ValueError on duplicate username.
    """
    # Normalise username to lowercase for uniqueness checks
    username = username.strip().lower()

    index = _load_index()
    if username in index:
        raise ValueError(f"Username '{username}' is already taken.")

    # Hash password — bcrypt.hashpw returns bytes
    pw_bytes = password.encode("utf-8")
    hashed = bcrypt.hashpw(pw_bytes, bcrypt.gensalt(rounds=12))

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    user_record = {
        "id": user_id,
        "username": username,
        "password_hash": hashed.decode("utf-8"),  # store as string
        "created_at": now,
    }

    # Persist user file first, then update index
    # (if the index write fails, the orphan user file is harmless)
    write_json(_user_file(user_id), user_record)

    index[username] = user_id
    _save_index(index)

    return {
        "id": user_id,
        "username": username,
        "created_at": now,
    }


def authenticate_user(username: str, password: str) -> dict:
    """
    Verify credentials and return a signed JWT.

    Returns { access_token, expires_in, user_id, username }.
    Raises ValueError if credentials are invalid.

    Note: uses a constant-time comparison path regardless of whether
    the username exists, to avoid user-enumeration via timing.
    """
    username = username.strip().lower()
    index = _load_index()

    # Always run bcrypt even on missing username (prevents timing attacks)
    dummy_hash = "$2b$12$invalidhashpadding000000000000000000000000000000000000"
    stored_hash = dummy_hash
    user_record = None

    if username in index:
        user_id = index[username]
        try:
            user_record = read_json(_user_file(user_id))
            stored_hash = user_record["password_hash"]
        except (FileNotFoundError, KeyError):
            stored_hash = dummy_hash

    pw_match = bcrypt.checkpw(
        password.encode("utf-8"),
        stored_hash.encode("utf-8"),
    )

    if not pw_match or user_record is None:
        raise ValueError("Invalid username or password.")

    # Issue JWT
    ttl = _token_ttl_minutes()
    expiry = datetime.now(timezone.utc) + timedelta(minutes=ttl)

    payload = {
        "sub": user_record["id"],        # subject = user_id
        "username": user_record["username"],
        "exp": expiry,
        "iat": datetime.now(timezone.utc),
    }

    token = jwt.encode(payload, _get_jwt_secret(), algorithm="HS256")

    return {
        "access_token": token,
        "expires_in": ttl * 60,          # seconds
        "user_id": user_record["id"],
        "username": user_record["username"],
    }


def verify_token(token: str) -> dict:
    """
    Decode and validate a JWT.

    Returns the decoded payload dict { sub, username, exp, iat }.
    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    """
    payload = jwt.decode(
        token,
        _get_jwt_secret(),
        algorithms=["HS256"],
    )
    return payload
