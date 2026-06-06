"""
models/secret.py
----------------
Secret data model.

Stored at: storage/secrets/{owner_id}/{secret_id}.json

Fields:
  id              — UUID4 string
  owner_id        — UUID4 of the owning user
  name            — human-readable label
  description     — optional free-text notes
  tags            — list of string labels
  encrypted_value — Fernet ciphertext (base64 string); NEVER the plaintext
  created_at      — ISO 8601 timestamp
  updated_at      — ISO 8601 timestamp (updated on PUT)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List
import uuid


@dataclass
class Secret:
    owner_id: str
    name: str
    encrypted_value: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        """Serialise to a dict for file storage. Includes encrypted_value."""
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "encrypted_value": self.encrypted_value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_metadata_dict(self) -> dict:
        """List-safe representation — omits encrypted_value."""
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
