"""
models/user.py
--------------
User data model.

Represents the structure of a user record stored at:
  storage/users/{user_id}.json

Fields:
  id          — UUID4 string
  username    — unique, alphanumeric
  password    — bcrypt hash (NEVER the plaintext password)
  created_at  — ISO 8601 timestamp
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid


@dataclass
class User:
    username: str
    password_hash: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        """Serialise to a dict for file storage. Includes the password hash."""
        return {
            "id": self.id,
            "username": self.username,
            "password_hash": self.password_hash,
            "created_at": self.created_at,
        }

    def to_public_dict(self) -> dict:
        """Safe representation — omits the password hash."""
        return {
            "id": self.id,
            "username": self.username,
            "created_at": self.created_at,
        }
