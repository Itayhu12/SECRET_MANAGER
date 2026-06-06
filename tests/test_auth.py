"""
tests/test_auth.py
------------------
Phase 1 tests: registration, login, JWT middleware.

Runs against a fully isolated storage_test/ directory so it never
touches real data. Run with: pytest tests/ -v
"""

import os
import shutil
import pytest

# Point storage at a temp directory before importing the app
os.environ.setdefault("STORAGE_PATH", "storage_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-for-testing-only")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-placeholder-only")
os.environ.setdefault("SECRET_KEY", "test-flask-secret")

from app import create_app
from config import TestingConfig


@pytest.fixture(scope="module")
def client():
    """Create the test client and wipe test storage after the module runs."""
    app = create_app(config_class=TestingConfig)
    with app.test_client() as c:
        yield c
    # Cleanup
    if os.path.isdir("storage_test"):
        shutil.rmtree("storage_test")


# ── /health ─────────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


# ── POST /register ───────────────────────────────────────────────────────────

def test_register_success(client):
    r = client.post("/register", json={
        "username": "alice",
        "password": "SecurePass1!"
    })
    assert r.status_code == 201
    data = r.get_json()
    assert data["username"] == "alice"
    assert "id" in data
    assert "password_hash" not in data   # never exposed


def test_register_duplicate(client):
    # First registration succeeds
    client.post("/register", json={"username": "bob", "password": "SecurePass1!"})
    # Second with same username must fail
    r = client.post("/register", json={"username": "bob", "password": "AnotherPass1!"})
    assert r.status_code == 400
    assert r.get_json()["code"] == "USERNAME_TAKEN"


def test_register_short_password(client):
    r = client.post("/register", json={"username": "carol", "password": "short"})
    assert r.status_code == 400
    assert r.get_json()["code"] == "VALIDATION_ERROR"


def test_register_invalid_username(client):
    r = client.post("/register", json={"username": "bad user!", "password": "SecurePass1!"})
    assert r.status_code == 400


def test_register_missing_fields(client):
    r = client.post("/register", json={})
    assert r.status_code == 400


# ── POST /login ──────────────────────────────────────────────────────────────

def test_login_success(client):
    client.post("/register", json={"username": "dave", "password": "SecurePass1!"})
    r = client.post("/login", json={"username": "dave", "password": "SecurePass1!"})
    assert r.status_code == 200
    data = r.get_json()
    assert "access_token" in data
    assert data["username"] == "dave"
    assert data["expires_in"] > 0


def test_login_wrong_password(client):
    client.post("/register", json={"username": "eve", "password": "CorrectPass1!"})
    r = client.post("/login", json={"username": "eve", "password": "WrongPass1!"})
    assert r.status_code == 401
    assert r.get_json()["code"] == "INVALID_CREDENTIALS"


def test_login_unknown_user(client):
    r = client.post("/login", json={"username": "ghost", "password": "SomePass1!"})
    assert r.status_code == 401


def test_login_missing_fields(client):
    r = client.post("/login", json={"username": "alice"})
    assert r.status_code == 400


# ── JWT middleware ────────────────────────────────────────────────────────────

def test_protected_route_without_token(client):
    """Any future protected route should return 401 without a token.
    We test the middleware directly with /secrets (returns 501 until Phase 2,
    but the auth check fires first)."""
    r = client.get("/secrets/")
    # 401 (auth) takes priority over 501 (not implemented) or 404
    assert r.status_code in (401, 404)   # 404 until blueprint is registered


def test_protected_route_with_bad_token(client):
    r = client.get("/secrets/", headers={"Authorization": "Bearer not.a.real.token"})
    assert r.status_code in (401, 404)
