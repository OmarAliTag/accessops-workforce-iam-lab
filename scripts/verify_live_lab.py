from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from accessops.exceptions import AccessOpsError  # noqa: E402
from scripts.common import build_audit_log, build_provider  # noqa: E402


def check(name: str, passed: bool, evidence: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "evidence": evidence}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the live AccessOps boundaries.")
    parser.add_argument(
        "--expect-canonical-scenario",
        action="store_true",
        help="Require the canonical Nadia joiner/mover/leaver result",
    )
    args = parser.parse_args()
    checks: list[dict[str, Any]] = []

    discovery = requests.get("http://127.0.0.1:8080/realms/accessops/.well-known/openid-configuration", timeout=5)
    discovery.raise_for_status()
    issuer = discovery.json().get("issuer")
    checks.append(
        check(
            "oidc_discovery",
            issuer == "http://127.0.0.1:8080/realms/accessops",
            {"status": discovery.status_code, "issuer": issuer},
        )
    )

    portal_health = requests.get("http://127.0.0.1:5000/health", timeout=5)
    portal_health.raise_for_status()
    health_body = portal_health.json()
    checks.append(
        check(
            "portal_health",
            health_body.get("status") == "ok",
            {"status": portal_health.status_code, "service": health_body.get("service")},
        )
    )

    home_response = requests.get("http://127.0.0.1:5000/", timeout=5)
    home_response.raise_for_status()
    checks.append(
        check(
            "portal_security_headers",
            "frame-ancestors 'none'" in home_response.headers.get("Content-Security-Policy", ""),
            {
                "status": home_response.status_code,
                "content_security_policy": home_response.headers.get("Content-Security-Policy", ""),
            },
        )
    )

    provider = build_provider()
    users = provider.list_users()
    usernames = [user.username for user in users]
    checks.append(
        check(
            "service_account_and_seed_users",
            {"nour.helpdesk", "dina.auditor"}.issubset(usernames),
            {"identity_count": len(users), "usernames": usernames},
        )
    )

    if args.expect_canonical_scenario:
        nadia = provider.get_user("nadia.hassan")
        canonical_passed = bool(
            nadia and not nadia.enabled and nadia.department == "Operations" and not nadia.groups and not nadia.roles
        )
        checks.append(
            check(
                "canonical_jml_final_state",
                canonical_passed,
                nadia.safe_dict() if nadia else None,
            )
        )

    audit_result = build_audit_log().verify_chain()
    checks.append(check("audit_chain", bool(audit_result["valid"]), audit_result))

    result = {
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
    }
    target = PROJECT_ROOT / "evidence" / "live-verification.json"
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (requests.RequestException, AccessOpsError, OSError, ValueError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, indent=2), file=sys.stderr)
        raise SystemExit(2) from exc
