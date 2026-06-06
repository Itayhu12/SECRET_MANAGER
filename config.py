"""
config.py
---------
Application configuration for development and production environments.
All sensitive values are read from environment variables via python-dotenv.
"""

import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()


class Config:
    """Base configuration — shared across all environments."""

    # ── Flask ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "")

    # ── JWT ────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "")
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES: int = int(
        os.environ.get("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", 60)
    )

    # ── Encryption ─────────────────────────────────────────────────────────
    ENCRYPTION_KEY: str = os.environ.get("ENCRYPTION_KEY", "")

    # ── File Storage ───────────────────────────────────────────────────────
    STORAGE_PATH: str = os.environ.get("STORAGE_PATH", "storage")

    # ── Share links ────────────────────────────────────────────────────────
    SHARE_DEFAULT_TTL_SECONDS: int = int(
        os.environ.get("SHARE_DEFAULT_TTL_SECONDS", 3600)
    )
    SHARE_MAX_TTL_SECONDS: int = int(
        os.environ.get("SHARE_MAX_TTL_SECONDS", 86400)
    )

    # ── Rate limiting ──────────────────────────────────────────────────────
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URI = "memory://"


class DevelopmentConfig(Config):
    """Development — verbose errors, debug mode on."""

    DEBUG: bool = True
    TESTING: bool = False


class ProductionConfig(Config):
    """Production — no debug, strict settings."""

    DEBUG: bool = False
    TESTING: bool = False

    @classmethod
    def validate(cls) -> None:
        """Raise at startup if any required secret is missing in production."""
        required = ["SECRET_KEY", "JWT_SECRET_KEY", "ENCRYPTION_KEY"]
        missing = [k for k in required if not os.environ.get(k)]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}"
            )


class TestingConfig(Config):
    """Testing — isolated storage path, no rate limits."""

    DEBUG: bool = True
    TESTING: bool = True
    STORAGE_PATH: str = "storage_test"
    RATELIMIT_ENABLED: bool = False


# ── Config selector ────────────────────────────────────────────────────────
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config() -> Config:
    """Return the config class matching the FLASK_ENV environment variable."""
    env = os.environ.get("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)
