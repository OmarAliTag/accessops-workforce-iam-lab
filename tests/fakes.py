from __future__ import annotations

from dataclasses import replace

from accessops.exceptions import IdentityConflict, IdentityNotFound
from accessops.models import Identity
from accessops.policy import roles_for_groups


class FakeIdentityProvider:
    def __init__(self):
        self.users: dict[str, Identity] = {}
        self.create_calls = 0
        self.move_calls = 0
        self.disable_calls = 0

    def get_user(self, username: str) -> Identity | None:
        return self.users.get(username)

    def list_users(self) -> list[Identity]:
        return sorted(self.users.values(), key=lambda user: user.username)

    def create_user(
        self,
        *,
        username: str,
        email: str,
        first_name: str,
        last_name: str,
        department: str,
        groups: tuple[str, ...],
    ) -> Identity:
        if username in self.users:
            raise IdentityConflict(f"Identity '{username}' already exists.")
        self.create_calls += 1
        required = ("CONFIGURE_TOTP", "UPDATE_PASSWORD") if department == "IAM Operations" else ("UPDATE_PASSWORD",)
        identity = Identity(
            id=f"fake-{len(self.users) + 1}",
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            enabled=True,
            department=department,
            groups=tuple(sorted(groups)),
            roles=roles_for_groups(groups),
            required_actions=required,
        )
        self.users[username] = identity
        return identity

    def move_user(self, username: str, department: str, groups: tuple[str, ...]) -> Identity:
        identity = self.users.get(username)
        if not identity:
            raise IdentityNotFound(username)
        if not identity.enabled:
            raise IdentityConflict(username)
        self.move_calls += 1
        required = set(identity.required_actions)
        if department == "IAM Operations":
            required.add("CONFIGURE_TOTP")
        moved = replace(
            identity,
            department=department,
            groups=tuple(sorted(groups)),
            roles=roles_for_groups(groups),
            required_actions=tuple(sorted(required)),
        )
        self.users[username] = moved
        return moved

    def disable_user(self, username: str) -> Identity:
        identity = self.users.get(username)
        if not identity:
            raise IdentityNotFound(username)
        if not identity.enabled:
            raise IdentityConflict(username)
        self.disable_calls += 1
        disabled = replace(identity, enabled=False, groups=(), roles=())
        self.users[username] = disabled
        return disabled
