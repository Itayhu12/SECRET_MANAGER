"""
routes/shares.py
----------------
POST /secrets/<id>/share   Generate one-time expiring token  (auth required)
GET  /share/<token>        Consume token, return secret       (no auth needed)

Phase 4 additions: audit logging on both endpoints.
"""

from flask import Blueprint, request, jsonify, g
from services import share_service
from utils.auth_middleware import require_auth
from utils.validators import validate_share_ttl
from utils.audit_logger import log_event
import os

shares_bp = Blueprint("shares", __name__)


@shares_bp.post("/secrets/<secret_id>/share")
@require_auth
def create_share(secret_id: str):
    user_id     = g.current_user["sub"]
    body        = request.get_json(silent=True) or {}
    default_ttl = int(os.environ.get("SHARE_DEFAULT_TTL_SECONDS", 3600))

    try:
        ttl = validate_share_ttl(body.get("ttl_seconds"), default=default_ttl)
    except ValueError as e:
        return jsonify({"error": str(e), "code": "VALIDATION_ERROR"}), 400

    try:
        result = share_service.create_share_token(user_id, secret_id, ttl)
    except FileNotFoundError as e:
        return jsonify({"error": str(e), "code": "NOT_FOUND"}), 404
    except PermissionError as e:
        return jsonify({"error": str(e), "code": "FORBIDDEN"}), 403

    log_event("share.create", user_id=user_id, secret_id=secret_id,
              token=result["token"], ip_address=request.remote_addr,
              extra={"ttl_seconds": ttl, "expires_at": result["expires_at"]})

    return jsonify(result), 201


@shares_bp.get("/share/<token>")
def access_share(token: str):
    ip = request.remote_addr
    try:
        result = share_service.consume_share_token(token)
    except FileNotFoundError:
        log_event("share.failed", user_id="anonymous",
                  token=token, ip_address=ip)
        return jsonify({
            "error": "Share token not found, already used, or expired.",
            "code":  "TOKEN_INVALID",
        }), 404

    log_event("share.consume", user_id="anonymous",
              token=token, ip_address=ip,
              extra={"accessed_at": result["accessed_at"]})
    return jsonify(result), 200