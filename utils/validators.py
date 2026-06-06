"""
utils/validators.py
-------------------
Input validation — called by routes before any business logic.
Each function returns the cleaned value or raises ValueError.

Phase 4 hardening: null-byte injection, oversized inputs,
non-string types, path traversal, UUID format check.
"""

import re
import uuid as _uuid

USERNAME_MIN    = 3;   USERNAME_MAX    = 50
PASSWORD_MIN    = 8;   PASSWORD_MAX    = 128
SECRET_NAME_MAX = 255; SECRET_VAL_MAX  = 10_000
DESCRIPTION_MAX = 1_000
TAG_MAX_LEN     = 50;  TAG_MAX_COUNT   = 10
SHARE_TTL_MAX   = 86_400

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]+$")


def _check_null_bytes(value: str, field: str) -> None:
    if "\x00" in value:
        raise ValueError(f"{field} must not contain null bytes.")


def validate_username(username: str) -> str:
    if not isinstance(username, str): raise ValueError("Username must be a string.")
    username = username.strip()
    _check_null_bytes(username, "Username")
    if len(username) < USERNAME_MIN: raise ValueError(f"Username must be at least {USERNAME_MIN} characters.")
    if len(username) > USERNAME_MAX: raise ValueError(f"Username must be at most {USERNAME_MAX} characters.")
    if not USERNAME_RE.match(username): raise ValueError("Username may only contain letters, digits, and underscores.")
    return username.lower()


def validate_password(password: str) -> str:
    if not isinstance(password, str): raise ValueError("Password must be a string.")
    _check_null_bytes(password, "Password")
    if len(password) < PASSWORD_MIN: raise ValueError(f"Password must be at least {PASSWORD_MIN} characters.")
    if len(password) > PASSWORD_MAX: raise ValueError(f"Password must be at most {PASSWORD_MAX} characters.")
    return password


def validate_secret_name(name: str) -> str:
    if not isinstance(name, str): raise ValueError("Secret name must be a string.")
    name = name.strip()
    _check_null_bytes(name, "Secret name")
    if not name: raise ValueError("Secret name must not be empty.")
    if len(name) > SECRET_NAME_MAX: raise ValueError(f"Secret name must be at most {SECRET_NAME_MAX} characters.")
    return name


def validate_secret_value(value: str) -> str:
    if not isinstance(value, str): raise ValueError("Secret value must be a string.")
    _check_null_bytes(value, "Secret value")
    if not value: raise ValueError("Secret value must not be empty.")
    if len(value) > SECRET_VAL_MAX: raise ValueError(f"Secret value must be at most {SECRET_VAL_MAX} characters.")
    return value


def validate_description(description: str) -> str:
    if not isinstance(description, str): raise ValueError("Description must be a string.")
    description = description.strip()
    _check_null_bytes(description, "Description")
    if len(description) > DESCRIPTION_MAX: raise ValueError(f"Description must be at most {DESCRIPTION_MAX} characters.")
    return description


def validate_tags(tags) -> list:
    if tags is None: return []
    if not isinstance(tags, list): raise ValueError("Tags must be a list of strings.")
    if len(tags) > TAG_MAX_COUNT: raise ValueError(f"At most {TAG_MAX_COUNT} tags are allowed.")
    cleaned = []
    for tag in tags:
        if not isinstance(tag, str): raise ValueError("Each tag must be a string.")
        tag = tag.strip()
        if not tag: continue
        _check_null_bytes(tag, "Tag")
        if len(tag) > TAG_MAX_LEN: raise ValueError(f"Each tag must be at most {TAG_MAX_LEN} characters.")
        cleaned.append(tag)
    return cleaned


def validate_share_ttl(ttl_seconds, default: int) -> int:
    if ttl_seconds is None: return default
    try: ttl = int(ttl_seconds)
    except (TypeError, ValueError): raise ValueError("ttl_seconds must be an integer.")
    if ttl < 1: raise ValueError("ttl_seconds must be at least 1.")
    if ttl > SHARE_TTL_MAX: raise ValueError(f"ttl_seconds must be at most {SHARE_TTL_MAX} (24 hours).")
    return ttl


def validate_uuid(value: str, field: str = "ID") -> str:
    if not isinstance(value, str): raise ValueError(f"{field} must be a string.")
    try: _uuid.UUID(value, version=4)
    except ValueError: raise ValueError(f"{field} is not a valid UUID.")
    return value.lower()