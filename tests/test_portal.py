from pathlib import Path

import pytest

from portal.app import create_app


@pytest.fixture()
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ACCESSOPS_AUDIT_LOG", str(tmp_path / "web-audit.jsonl"))
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "OIDC_CLIENT_SECRET": "test-client-secret",
        }
    )


def set_identity(client, roles: list[str]) -> None:
    with client.session_transaction() as session:
        session["identity"] = {
            "subject": "subject-1",
            "username": "nour.helpdesk",
            "name": "Nour Haddad",
            "email": "nour.helpdesk@example.test",
            "roles": roles,
        }


def test_public_home_and_health(app) -> None:
    client = app.test_client()
    assert client.get("/").status_code == 200
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json["service"] == "accessops-portal"


def test_employee_is_allowed_to_dashboard_and_tickets(app) -> None:
    client = app.test_client()
    set_identity(client, ["portal-user", "ticket-reader"])
    assert client.get("/dashboard").status_code == 200
    assert client.get("/tickets").status_code == 200


def test_employee_is_denied_iam_admin_and_denial_is_audited(app, tmp_path: Path) -> None:
    client = app.test_client()
    set_identity(client, ["portal-user", "ticket-reader"])
    response = client.get("/iam-admin")
    assert response.status_code == 403
    audit_text = (tmp_path / "web-audit.jsonl").read_text(encoding="utf-8")
    assert "authorization.denied" in audit_text
    assert "iam-admin" in audit_text


def test_iam_admin_is_allowed_privileged_routes(app) -> None:
    client = app.test_client()
    set_identity(client, ["portal-user", "iam-admin", "auditor"])
    assert client.get("/iam-admin").status_code == 200
    assert client.get("/audit").status_code == 200
