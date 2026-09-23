from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

GROUP_DEPARTMENTS = {
    "Helpdesk": "Helpdesk",
    "IAM-Operations": "IAM Operations",
    "Finance-Requesters": "Finance Requesting",
    "Finance-Approvers": "Finance Approval",
    "Operations": "Operations",
}


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value or value.startswith(("replace-", "Replace-")):
        raise RuntimeError(f"Set {name} in .env before configuring the realm.")
    return value


def admin_token(base_url: str) -> str:
    response = requests.post(
        f"{base_url}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": required_env("KEYCLOAK_BOOTSTRAP_ADMIN"),
            "password": required_env("KEYCLOAK_BOOTSTRAP_PASSWORD"),
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def managed_attribute(name: str, display_name: str, maximum: int) -> dict[str, Any]:
    return {
        "name": name,
        "displayName": display_name,
        "validations": {"length": {"max": maximum}},
        "permissions": {"view": ["admin"], "edit": ["admin"]},
        "multivalued": False,
    }


def main() -> int:
    base_url = os.environ.get("KEYCLOAK_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
    realm = os.environ.get("KEYCLOAK_REALM", "accessops")
    token = admin_token(base_url)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    admin_base = f"{base_url}/admin/realms/{realm}"

    profile_response = requests.get(f"{admin_base}/users/profile", headers=headers, timeout=10)
    profile_response.raise_for_status()
    profile = profile_response.json()
    attributes = {row["name"]: row for row in profile.get("attributes", [])}
    attributes["department"] = managed_attribute("department", "Department", 64)
    attributes["data_classification"] = managed_attribute("data_classification", "Data classification", 32)
    profile["attributes"] = list(attributes.values())
    update_profile = requests.put(f"{admin_base}/users/profile", headers=headers, json=profile, timeout=10)
    if not update_profile.ok:
        detail = update_profile.text[:500].replace("\n", " ")
        raise RuntimeError(f"User-profile update failed with HTTP {update_profile.status_code}: {detail}")
    update_profile.raise_for_status()

    users_response = requests.get(f"{admin_base}/users", headers=headers, params={"first": 0, "max": 1000}, timeout=10)
    users_response.raise_for_status()
    configured: list[str] = []
    for user in users_response.json():
        username = user.get("username", "")
        if username.startswith("service-account-"):
            continue
        groups_response = requests.get(f"{admin_base}/users/{user['id']}/groups", headers=headers, timeout=10)
        groups_response.raise_for_status()
        group_names = {group["name"] for group in groups_response.json()}
        department = next((value for group, value in GROUP_DEPARTMENTS.items() if group in group_names), "")
        if not department:
            continue
        user["attributes"] = {
            **(user.get("attributes") or {}),
            "department": [department],
            "data_classification": ["synthetic"],
        }
        update_user = requests.put(f"{admin_base}/users/{user['id']}", headers=headers, json=user, timeout=10)
        update_user.raise_for_status()
        configured.append(username)

    service_response = requests.post(
        f"{base_url}/realms/{realm}/protocol/openid-connect/token",
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ.get("KEYCLOAK_AUTOMATION_CLIENT_ID", "accessops-automation"),
            "client_secret": required_env("KEYCLOAK_AUTOMATION_CLIENT_SECRET"),
        },
        timeout=10,
    )
    service_response.raise_for_status()
    service_token = service_response.json()["access_token"]
    service_check = requests.get(
        f"{admin_base}/users",
        headers={"Authorization": f"Bearer {service_token}"},
        params={"max": 1},
        timeout=10,
    )
    service_check.raise_for_status()

    verify_profile = requests.get(f"{admin_base}/users/profile", headers=headers, timeout=10)
    verify_profile.raise_for_status()
    profile_names = {row["name"] for row in verify_profile.json().get("attributes", [])}
    result = {
        "realm": realm,
        "managed_attributes": sorted(profile_names & {"department", "data_classification"}),
        "identities_updated": sorted(configured),
        "service_account_verified": service_check.status_code == 200,
    }
    print(json.dumps(result, indent=2))
    return 0 if len(result["managed_attributes"]) == 2 and result["service_account_verified"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (requests.RequestException, RuntimeError, KeyError, ValueError) as exc:
        print(json.dumps({"outcome": "failure", "error": str(exc)}, indent=2), file=sys.stderr)
        raise SystemExit(2) from exc
