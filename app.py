"""
app.py — Flask application factory.

Phase 4 additions:
  - Flask-Limiter with strict limits on auth endpoints
  - Global default rate limit on all routes
  - Limit error handler returns consistent JSON envelope

Run: flask run   |   python app.py
"""

from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import get_config

# ── Limiter instance (attached to app in create_app) ───────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)


def create_app(config_class=None) -> Flask:
    app = Flask(__name__)
    cfg = config_class or get_config()
    app.config.from_object(cfg)

    # ── Rate limiter ───────────────────────────────────────────────────────
    limiter.init_app(app)

    # ── Blueprints ─────────────────────────────────────────────────────────
    from routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from routes.secrets import secrets_bp
    app.register_blueprint(secrets_bp)

    from routes.shares import shares_bp
    app.register_blueprint(shares_bp)

    # ── Tighter limits on auth endpoints ──────────────────────────────────
    limiter.limit("5 per minute")(app.view_functions["auth.register"])
    limiter.limit("10 per minute")(app.view_functions["auth.login"])

    # ── Rate limit exceeded handler ────────────────────────────────────────
    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify({
            "error": "Too many requests. Please slow down and try again later.",
            "code":  "RATE_LIMIT_EXCEEDED",
        }), 429

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Endpoint not found.", "code": "NOT_FOUND"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed.", "code": "METHOD_NOT_ALLOWED"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Internal server error.", "code": "INTERNAL_ERROR"}), 500

    @app.get("/health")
    @limiter.exempt
    def health():
        return jsonify({
            "status": "ok",
            "env": "development" if app.config.get("DEBUG") else "production",
        })

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)