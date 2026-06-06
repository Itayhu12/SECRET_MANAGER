"""
models/share.py
---------------
Share token data model.

Stored at: storage/shares/{token}.json

Fields:
  token       — cryptographically random URL-safe string (32 bytes)
  secret_id   — UUID4 of the target secret
  owner_id    — UUID4 of the user who created this share
  expires_at  — ISO 8601 timestamp; token is invalid after this
  used        — bool; True after the token has been consumed once
  created_at  — ISO 8601 timestamp
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ShareToken:
    token: str
    secret_id: str
    owner_id: str
    expires_at: str
    used: bool = False
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "secret_id": self.secret_id,
            "owner_id": self.owner_id,
            "expires_at": self.expires_at,
            "used": self.used,
            "created_at": self.created_at,
        }

    def is_valid(self) -> bool:
        """Return True if the token is unused and not yet expired."""
        if self.used:
            return False
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.now(timezone.utc) < expires
