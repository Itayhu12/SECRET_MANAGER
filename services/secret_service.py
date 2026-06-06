"""
services/secret_service.py
--------------------------
CRUD operations for user secrets.

Storage layout
--------------
  storage/secrets/<owner_id>/<secret_id>.json

Security rules
--------------
  1. Every operation checks owner_id before proceeding.
  2. encrypted_value is written to disk; plaintext only lives in memory.
  3. List endpoint returns metadata only — never encrypted_value.
"""

import os, uuid
from datetime import datetime, timezone
from services.crypto_service import encrypt, decrypt
from utils.file_storage import (
    read_json, write_json, delete_file,
    file_exists, list_json_files, build_path
)

def _storage_root() -> str:
    return os.environ.get("STORAGE_PATH", "storage")

def _secret_dir(owner_id: str) -> str:
    return build_path(_storage_root(), "secrets", owner_id)

def _secret_file(owner_id: str, secret_id: str) -> str:
    return build_path(_secret_dir(owner_id), secret_id + ".json")

def _load_and_verify(owner_id: str, secret_id: str) -> dict:
    """Load file and verify ownership. Raises FileNotFoundError or PermissionError."""
    path = _secret_file(owner_id, secret_id)
    if file_exists(path):
        data = read_json(path)
        if data.get("owner_id") != owner_id:
            raise PermissionError("You do not have access to this secret.")
        return data
    raise FileNotFoundError(f"Secret '{secret_id}' not found.")

def create_secret(owner_id, name, value, description="", tags=None) -> dict:
    secret_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "id": secret_id, "owner_id": owner_id, "name": name,
        "description": description, "tags": tags or [],
        "encrypted_value": encrypt(value),   # plaintext never hits disk
        "created_at": now, "updated_at": now,
    }
    write_json(_secret_file(owner_id, secret_id), record)
    return _to_metadata(record)

def get_secret(owner_id, secret_id) -> dict:
    """Only function that returns a plaintext value."""
    data = _load_and_verify(owner_id, secret_id)
    return {**_to_metadata(data), "value": decrypt(data["encrypted_value"])}

def update_secret(owner_id, secret_id, name=None, description=None, tags=None) -> dict:
    data = _load_and_verify(owner_id, secret_id)
    if name is not None: data["name"] = name
    if description is not None: data["description"] = description
    if tags is not None: data["tags"] = tags
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_json(_secret_file(owner_id, secret_id), data)
    return _to_metadata(data)

def delete_secret(owner_id, secret_id) -> None:
    _load_and_verify(owner_id, secret_id)
    delete_file(_secret_file(owner_id, secret_id))

def list_secrets(owner_id) -> list:
    paths = list_json_files(_secret_dir(owner_id))
    secrets = []
    for path in paths:
        try:
            data = read_json(path)
            if data.get("owner_id") == owner_id:
                secrets.append(_to_metadata(data))
        except (KeyError, ValueError):
            continue
    return sorted(secrets, key=lambda s: s["created_at"], reverse=True)

def _to_metadata(data: dict) -> dict:
    """Strip encrypted_value — never returned in list or metadata responses."""
    return {k: data[k] for k in
            ("id","owner_id","name","description","tags","created_at","updated_at")}