from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Identity:
    id: str
    username: str
    email: str
    first_name: str
    last_name: str
    enabled: bool
    department: str
    groups: tuple[str, ...] = field(default_factory=tuple)
    roles: tuple[str, ...] = field(default_factory=tuple)
    required_actions: tuple[str, ...] = field(default_factory=tuple)

    def safe_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "enabled": self.enabled,
            "department": self.department,
            "groups": list(self.groups),
            "roles": list(self.roles),
            "required_actions": list(self.required_actions),
        }


@dataclass(frozen=True)
class LifecycleResult:
    event_id: str
    action: str
    outcome: str
    replayed: bool
    identity: Identity
    message: str

    def safe_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "action": self.action,
            "outcome": self.outcome,
            "replayed": self.replayed,
            "identity": self.identity.safe_dict(),
            "message": self.message,
        }
