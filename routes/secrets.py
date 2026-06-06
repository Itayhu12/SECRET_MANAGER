"""
routes/secrets.py
-----------------
GET    /secrets/       List all secrets (metadata only)
POST   /secrets/       Create a new encrypted secret
GET    /secrets/<id>   Retrieve + decrypt a secret
PUT    /secrets/<id>   Update secret metadata
DELETE /secrets/<id>   Delete a secret

Phase 4 additions: audit logging on every endpoint.
"""

from flask import Blueprint, request, jsonify, g
from services import secret_service
from utils.auth_middleware import require_auth
from utils import validators
from utils.audit_logger import log_event

secrets_bp = Blueprint("secrets", __name__, url_prefix="/secrets")


@secrets_bp.get("/")
@require_auth
def list_secrets():
    user_id = g.current_user["sub"]
    secrets = secret_service.list_secrets(user_id)
    log_event("secret.list", user_id=user_id,
              ip_address=request.remote_addr, extra={"count": len(secrets)})
    return jsonify(secrets), 200


@secrets_bp.post("/")
@require_auth
def create_secret():
    user_id = g.current_user["sub"]
    body    = request.get_json(silent=True) or {}
    try:
        name        = validators.validate_secret_name(body.get("name", ""))
        value       = validators.validate_secret_value(body.get("value", ""))
        description = validators.validate_description(body.get("description", ""))
        tags        = validators.validate_tags(body.get("tags"))
    except ValueError as e:
        return jsonify({"error": str(e), "code": "VALIDATION_ERROR"}), 400

    secret = secret_service.create_secret(user_id, name, value, description, tags)
    log_event("secret.create", user_id=user_id, secret_id=secret["id"],
              ip_address=request.remote_addr, extra={"name": name})
    return jsonify(secret), 201


@secrets_bp.get("/<secret_id>")
@require_auth
def get_secret(secret_id: str):
    user_id = g.current_user["sub"]
    try:
        secret = secret_service.get_secret(user_id, secret_id)
    except FileNotFoundError:
        return jsonify({"error": "Secret not found.", "code": "NOT_FOUND"}), 404
    except PermissionError:
        log_event("secret.access_denied", user_id=user_id,
                  secret_id=secret_id, ip_address=request.remote_addr)
        return jsonify({"error": "Access denied.", "code": "FORBIDDEN"}), 403

    log_event("secret.read", user_id=user_id,
              secret_id=secret_id, ip_address=request.remote_addr)
    return jsonify(secret), 200


@secrets_bp.put("/<secret_id>")
@require_auth
def update_secret(secret_id: str):
    user_id = g.current_user["sub"]
    body    = request.get_json(silent=True) or {}
    try:
        name        = validators.validate_secret_name(body["name"])        if "name"        in body else None
        description = validators.validate_description(body["description"]) if "description" in body else None
        tags        = validators.validate_tags(body["tags"])               if "tags"        in body else None
    except ValueError as e:
        return jsonify({"error": str(e), "code": "VALIDATION_ERROR"}), 400

    if all(v is None for v in (name, description, tags)):
        return jsonify({"error": "Provide at least one field to update.", "code": "VALIDATION_ERROR"}), 400

    try:
        secret = secret_service.update_secret(user_id, secret_id, name, description, tags)
    except FileNotFoundError:
        return jsonify({"error": "Secret not found.", "code": "NOT_FOUND"}), 404
    except PermissionError:
        return jsonify({"error": "Access denied.", "code": "FORBIDDEN"}), 403

    log_event("secret.update", user_id=user_id, secret_id=secret_id,
              ip_address=request.remote_addr,
              extra={"fields_updated": [k for k, v in
                     {"name": name, "description": description, "tags": tags}.items()
                     if v is not None]})
    return jsonify(secret), 200


@secrets_bp.delete("/<secret_id>")
@require_auth
def delete_secret(secret_id: str):
    user_id = g.current_user["sub"]
    try:
        secret_service.delete_secret(user_id, secret_id)
    except FileNotFoundError:
        return jsonify({"error": "Secret not found.", "code": "NOT_FOUND"}), 404
    except PermissionError:
        return jsonify({"error": "Access denied.", "code": "FORBIDDEN"}), 403

    log_event("secret.delete", user_id=user_id,
              secret_id=secret_id, ip_address=request.remote_addr)
    return "", 204