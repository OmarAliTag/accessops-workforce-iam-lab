import json
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_realm_has_required_clients_groups_roles_and_synthetic_users() -> None:
    realm = json.loads((PROJECT_ROOT / "keycloak" / "accessops-realm.json").read_text(encoding="utf-8"))
    assert realm["realm"] == "accessops"
    assert {client["clientId"] for client in realm["clients"]} == {
        "accessops-automation",
        "accessops-portal",
    }
    assert {group["name"] for group in realm["groups"]} >= {
        "Employees",
        "Helpdesk",
        "IAM-Operations",
        "Finance-Requesters",
        "Finance-Approvers",
        "Operations",
    }
    people = [user for user in realm["users"] if not user["username"].startswith("service-account-")]
    assert all(user["email"].endswith("@example.test") for user in people)


def test_optional_compose_profile_is_pinned_and_loopback_only() -> None:
    compose = yaml.safe_load((PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8"))
    keycloak = compose["services"]["keycloak"]
    assert keycloak["image"] == "quay.io/keycloak/keycloak:26.7.4"
    assert keycloak["ports"] == ["127.0.0.1:8080:8080"]
    assert any("accessops-realm.json" in volume for volume in keycloak["volumes"])


def test_required_documentation_exists() -> None:
    expected = {
        "ARCHITECTURE.md",
        "CONTROL_MATRIX.md",
        "OKTA_MIGRATION.md",
        "RESEARCH.md",
        "RUNBOOK.md",
    }
    assert expected.issubset({path.name for path in (PROJECT_ROOT / "docs").glob("*.md")})
