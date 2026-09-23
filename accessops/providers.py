from __future__ import annotations

import time
from typing import Any, Protocol

import requests

from .exceptions import IdentityConflict, IdentityNotFound, ProviderError
from .models import Identity
from .policy import MANAGED_GROUPS, roles_for_groups


class IdentityProvider(Protocol):
    def get_user(self, username: str) -> Identity | None: ...

    def list_users(self) -> list[Identity]: ...

    def create_user(
        self,
        *,
        username: str,
        email: str,
        first_name: str,
        last_name: str,
        department: str,
        groups: tuple[str, ...],
    ) -> Identity: ...

    def move_user(self, username: str, department: str, groups: tuple[str, ...]) -> Identity: ...

    def disable_user(self, username: str) -> Identity: ...


class KeycloakProvider:
    """Small Keycloak Admin REST adapter using a least-privilege service account."""

    def __init__(
        self,
        *,
        base_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
        temporary_password: str,
        timeout_seconds: int = 10,
    ):
        self.base_url = base_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        self.temporary_password = temporary_password
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self._token = ""
        self._token_expires_at = 0.0
        self._group_ids: dict[str, str] = {}

    def _authenticate(self) -> None:
        try:
            response = self.session.post(
                f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            self._token = body["access_token"]
            self._token_expires_at = time.time() + int(body.get("expires_in", 60)) - 10
        except (requests.RequestException, KeyError, ValueError) as exc:
            raise ProviderError("Keycloak service-account authentication failed.") from exc

    def _request(
        self,
        method: str,
        path: str,
        *,
        expected: tuple[int, ...] = (200,),
        retry_auth: bool = True,
        **kwargs: Any,
    ) -> requests.Response:
        if not self._token or time.time() >= self._token_expires_at:
            self._authenticate()
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {self._token}"
        headers.setdefault("Accept", "application/json")
        try:
            response = self.session.request(
                method,
                f"{self.base_url}/admin/realms/{self.realm}{path}",
                headers=headers,
                timeout=self.timeout_seconds,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise ProviderError(f"Keycloak request failed for {method} {path}.") from exc

        if response.status_code == 401 and retry_auth:
            self._token = ""
            return self._request(method, path, expected=expected, retry_auth=False, **kwargs)
        if response.status_code not in expected:
            safe_detail = response.text[:240].replace("\n", " ")
            raise ProviderError(f"Keycloak returned HTTP {response.status_code} for {method} {path}: {safe_detail}")
        return response

    def _raw_user(self, username: str) -> dict[str, Any] | None:
        response = self._request(
            "GET",
            "/users",
            params={"username": username, "exact": "true", "max": 2},
        )
        matches = response.json()
        exact = [row for row in matches if row.get("username", "").casefold() == username.casefold()]
        if len(exact) > 1:
            raise ProviderError(f"Keycloak returned duplicate exact users for '{username}'.")
        return exact[0] if exact else None

    def _group_memberships(self, user_id: str) -> tuple[str, ...]:
        response = self._request("GET", f"/users/{user_id}/groups", params={"max": 100})
        return tuple(sorted(row["name"] for row in response.json() if row.get("name") in MANAGED_GROUPS))

    def _identity_from_raw(self, raw: dict[str, Any]) -> Identity:
        groups = self._group_memberships(raw["id"])
        attributes = raw.get("attributes") or {}
        department_values = attributes.get("department") or [""]
        return Identity(
            id=raw["id"],
            username=raw.get("username", ""),
            email=raw.get("email", ""),
            first_name=raw.get("firstName", ""),
            last_name=raw.get("lastName", ""),
            enabled=bool(raw.get("enabled")),
            department=department_values[0] if department_values else "",
            groups=groups,
            roles=roles_for_groups(groups),
            required_actions=tuple(sorted(raw.get("requiredActions") or [])),
        )

    def get_user(self, username: str) -> Identity | None:
        raw = self._raw_user(username)
        return self._identity_from_raw(raw) if raw else None

    def list_users(self) -> list[Identity]:
        response = self._request("GET", "/users", params={"first": 0, "max": 1000})
        users = [
            self._identity_from_raw(row)
            for row in response.json()
            if not row.get("username", "").startswith("service-account-")
        ]
        return sorted(users, key=lambda user: user.username)

    def _group_id(self, name: str) -> str:
        if name in self._group_ids:
            return self._group_ids[name]
        response = self._request("GET", "/groups", params={"search": name, "exact": "true", "max": 50})
        matches = [row for row in response.json() if row.get("name") == name]
        if len(matches) != 1:
            raise ProviderError(f"Expected one Keycloak group named '{name}', found {len(matches)}.")
        self._group_ids[name] = matches[0]["id"]
        return matches[0]["id"]

    def _set_groups(self, user_id: str, desired: tuple[str, ...]) -> None:
        current = set(self._group_memberships(user_id))
        wanted = set(desired)
        # Remove obsolete access first so a mover never temporarily holds both old and new access.
        for group in sorted(current - wanted):
            self._request("DELETE", f"/users/{user_id}/groups/{self._group_id(group)}", expected=(204,))
        for group in sorted(wanted - current):
            self._request("PUT", f"/users/{user_id}/groups/{self._group_id(group)}", expected=(204,))

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
        if self._raw_user(username):
            raise IdentityConflict(f"Identity '{username}' already exists.")
        required_actions = ["UPDATE_PASSWORD"]
        if department == "IAM Operations":
            required_actions.insert(0, "CONFIGURE_TOTP")
        payload = {
            "username": username,
            "email": email,
            "emailVerified": True,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": True,
            "attributes": {"department": [department], "data_classification": ["synthetic"]},
            "requiredActions": required_actions,
        }
        self._request("POST", "/users", json=payload, expected=(201,))
        raw = self._raw_user(username)
        if not raw:
            raise ProviderError(f"Keycloak did not return newly created identity '{username}'.")
        self._request(
            "PUT",
            f"/users/{raw['id']}/reset-password",
            json={"type": "password", "value": self.temporary_password, "temporary": True},
            expected=(204,),
        )
        self._set_groups(raw["id"], groups)
        created = self.get_user(username)
        if not created:
            raise ProviderError(f"Identity '{username}' disappeared after creation.")
        return created

    def move_user(self, username: str, department: str, groups: tuple[str, ...]) -> Identity:
        raw = self._raw_user(username)
        if not raw:
            raise IdentityNotFound(f"Identity '{username}' was not found.")
        if not raw.get("enabled"):
            raise IdentityConflict(f"Disabled identity '{username}' cannot be moved.")
        self._set_groups(raw["id"], groups)
        attributes = raw.get("attributes") or {}
        attributes["department"] = [department]
        raw["attributes"] = attributes
        required = set(raw.get("requiredActions") or [])
        if department == "IAM Operations":
            required.add("CONFIGURE_TOTP")
        raw["requiredActions"] = sorted(required)
        self._request("PUT", f"/users/{raw['id']}", json=raw, expected=(204,))
        moved = self.get_user(username)
        if not moved:
            raise ProviderError(f"Identity '{username}' disappeared after mover processing.")
        return moved

    def disable_user(self, username: str) -> Identity:
        raw = self._raw_user(username)
        if not raw:
            raise IdentityNotFound(f"Identity '{username}' was not found.")
        if not raw.get("enabled"):
            raise IdentityConflict(f"Identity '{username}' is already disabled.")
        self._set_groups(raw["id"], ())
        raw["enabled"] = False
        self._request("PUT", f"/users/{raw['id']}", json=raw, expected=(204,))
        self._request("POST", f"/users/{raw['id']}/logout", expected=(204,))
        disabled = self.get_user(username)
        if not disabled:
            raise ProviderError(f"Identity '{username}' disappeared after leaver processing.")
        return disabled
