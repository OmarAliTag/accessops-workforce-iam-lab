from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .policy import PRIVILEGED_ROLES, SOD_CONFLICT
from .providers import IdentityProvider


def build_review_rows(provider: IdentityProvider) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for identity in provider.list_users():
        group_set = set(identity.groups)
        role_set = set(identity.roles)
        exceptions: list[str] = []
        if SOD_CONFLICT.issubset(group_set):
            exceptions.append("SoD conflict: requester and approver")
        if not identity.enabled and identity.groups:
            exceptions.append("Disabled identity retains managed groups")
        if "iam-admin" in role_set and "CONFIGURE_TOTP" in identity.required_actions:
            exceptions.append("Privileged user has not completed TOTP enrollment")
        rows.append(
            {
                "identity_id": identity.id,
                "username": identity.username,
                "email": identity.email,
                "enabled": identity.enabled,
                "department": identity.department,
                "groups": ";".join(identity.groups),
                "roles": ";".join(identity.roles),
                "privileged": bool(role_set & PRIVILEGED_ROLES),
                "exceptions": "; ".join(exceptions),
                "review_recommendation": "REMOVE/REMEDIATE" if exceptions else "KEEP",
            }
        )
    return rows


def write_review(provider: IdentityProvider, csv_path: str | Path, json_path: str | Path) -> dict[str, Any]:
    rows = build_review_rows(provider)
    csv_target = Path(csv_path)
    json_target = Path(json_path)
    csv_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "identity_id",
        "username",
        "email",
        "enabled",
        "department",
        "groups",
        "roles",
        "privileged",
        "exceptions",
        "review_recommendation",
    ]
    with csv_target.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    report = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "identity_count": len(rows),
        "enabled_count": sum(bool(row["enabled"]) for row in rows),
        "privileged_count": sum(bool(row["privileged"]) for row in rows),
        "exception_count": sum(bool(row["exceptions"]) for row in rows),
        "rows": rows,
    }
    json_target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report
