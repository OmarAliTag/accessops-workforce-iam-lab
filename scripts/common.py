from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from accessops.audit import AuditLog
from accessops.exceptions import ValidationError
from accessops.providers import KeycloakProvider

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value or value.startswith("replace-") or value.startswith("Replace-"):
        raise ValidationError(f"Set {name} in .env before running this command.")
    return value


def build_provider() -> KeycloakProvider:
    return KeycloakProvider(
        base_url=os.environ.get("KEYCLOAK_BASE_URL", "http://127.0.0.1:8080"),
        realm=os.environ.get("KEYCLOAK_REALM", "accessops"),
        client_id=os.environ.get("KEYCLOAK_AUTOMATION_CLIENT_ID", "accessops-automation"),
        client_secret=required_env("KEYCLOAK_AUTOMATION_CLIENT_SECRET"),
        temporary_password=required_env("JOINER_TEMPORARY_PASSWORD"),
    )


def build_audit_log() -> AuditLog:
    configured = Path(os.environ.get("ACCESSOPS_AUDIT_LOG", "evidence/audit-log.jsonl"))
    path = configured if configured.is_absolute() else PROJECT_ROOT / configured
    return AuditLog(path)
