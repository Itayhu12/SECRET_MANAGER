"""
utils/auth_middleware.py
------------------------
@require_auth decorator — protects routes with JWT verification.

Usage:
    from utils.auth_middleware import require_auth
    from flask import g

    @secrets_bp.get("/<secret_id>")
    @require_auth
    def get_secret(secret_id):
        user_id  = g.current_user["sub"]
        username = g.current_user["username"]
"""

from functools import wraps
import jwt
from flask import g, request, jsonify
from services.auth_service import verify_token


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return jsonify({
                "error": "Authorization header missing or malformed.",
                "code": "MISSING_TOKEN",
            }), 401

        token = auth_header[len("Bearer "):]

        try:
            payload = verify_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({
                "error": "Token has expired. Please log in again.",
                "code": "TOKEN_EXPIRED",
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                "error": "Invalid token.",
                "code": "INVALID_TOKEN",
            }), 401

        g.current_user = payload   # { sub, username, exp, iat }
        return f(*args, **kwargs)

    return decorated