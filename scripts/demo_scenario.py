from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from accessops.exceptions import AccessOpsError  # noqa: E402
from accessops.lifecycle import LifecycleService  # noqa: E402
from scripts.common import build_audit_log, build_provider  # noqa: E402


def show(label: str, result) -> None:
    print(f"\n=== {label} ===")
    print(json.dumps(result.safe_dict(), indent=2))


def pause(message: str, enabled: bool) -> None:
    if enabled:
        input(f"\n{message} Press Enter to continue...")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a fresh guided joiner-mover-leaver demo.")
    parser.add_argument("--no-pause", action="store_true", help="Run the three stages without prompts")
    args = parser.parse_args()

    stamp = datetime.now(UTC).strftime("%H%M%S")
    run_id = uuid.uuid4().hex[:8].upper()
    username = f"nadia.demo.{stamp}"
    ticket_base = int(stamp) + 100000
    service = LifecycleService(build_provider(), build_audit_log())

    joiner = {
        "event_id": f"EVT-DEMO-{run_id}-J",
        "action": "joiner",
        "ticket_id": f"IAM-{ticket_base}",
        "requested_by": "hr.partner",
        "approved_by": "finance.manager",
        "reason": "Live demo joiner for the Finance requesting baseline.",
        "username": username,
        "first_name": "Nadia",
        "last_name": "Demo",
        "email": f"{username}@example.test",
        "department": "Finance Requesting",
    }
    mover = {
        "event_id": f"EVT-DEMO-{run_id}-M",
        "action": "mover",
        "ticket_id": f"IAM-{ticket_base + 1}",
        "requested_by": "operations.manager",
        "approved_by": "iam.reviewer",
        "reason": "Live demo transfer from Finance requesting to Operations.",
        "username": username,
        "from_department": "Finance Requesting",
        "to_department": "Operations",
    }
    leaver = {
        "event_id": f"EVT-DEMO-{run_id}-L",
        "action": "leaver",
        "ticket_id": f"IAM-{ticket_base + 2}",
        "requested_by": "hr.partner",
        "approved_by": "iam.reviewer",
        "reason": "Live demo leaver; disable access and revoke sessions.",
        "username": username,
    }

    try:
        created = service.process(joiner, actor="guided-demo")
        show("JOINER: least-privilege Finance access", created)
        pause("Point out the immutable identity ID and finance-requester role.", not args.no_pause)

        moved = service.process(mover, actor="guided-demo")
        show("MOVER: old access removed before Operations access", moved)
        pause("Point out that finance-requester disappeared and operations-user appeared.", not args.no_pause)

        disabled = service.process(leaver, actor="guided-demo")
        show("LEAVER: identity disabled, groups removed, sessions revoked", disabled)
    except (AccessOpsError, OSError) as exc:
        print(json.dumps({"outcome": "failure", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2

    print(f"\nScenario complete for synthetic identity: {username}")
    print("Next: run scripts\\access_review.py and scripts\\verify_audit.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
