"""
routes/auth.py
--------------
POST /register   Create a new user account
POST /login      Authenticate and receive a JWT

Phase 4 additions: audit logging on both endpoints.
"""

from flask import Blueprint, request, jsonify
from services import auth_service
from utils import validators
from utils.audit_logger import log_event, log_auth_failure

auth_bp = Blueprint("auth", __name__, url_prefix="/")


@auth_bp.post("/register")
def register():
    ip   = request.remote_addr
    body = request.get_json(silent=True) or {}

    try:
        username = validators.validate_username(body.get("username", ""))
        password = validators.validate_password(body.get("password", ""))
    except ValueError as e:
        return jsonify({"error": str(e), "code": "VALIDATION_ERROR"}), 400

    try:
        user = auth_service.register_user(username, password)
    except ValueError as e:
        return jsonify({"error": str(e), "code": "USERNAME_TAKEN"}), 400

    log_event("auth.register", user_id=user["id"],
              ip_address=ip, extra={"username": username})

    return jsonify(user), 201


@auth_bp.post("/login")
def login():
    ip   = request.remote_addr
    body = request.get_json(silent=True) or {}

    username = body.get("username", "")
    password = body.get("password", "")

    if not username or not password:
        return jsonify({
            "error": "Both 'username' and 'password' are required.",
            "code":  "VALIDATION_ERROR",
        }), 400

    try:
        result = auth_service.authenticate_user(username, password)
    except ValueError as e:
        log_auth_failure(username_hint=username, ip_address=ip)
        return jsonify({"error": str(e), "code": "INVALID_CREDENTIALS"}), 401

    log_event("auth.login", user_id=result["user_id"],
              ip_address=ip, extra={"username": result["username"]})

    return jsonify(result), 200