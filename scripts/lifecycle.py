from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from accessops.exceptions import AccessOpsError  # noqa: E402
from accessops.lifecycle import LifecycleService  # noqa: E402
from scripts.common import build_audit_log, build_provider  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Process one synthetic joiner, mover, or leaver request through Keycloak."
    )
    parser.add_argument("request", type=Path, help="Path to one JSON change request")
    args = parser.parse_args()

    try:
        payload = json.loads(args.request.read_text(encoding="utf-8"))
        service = LifecycleService(build_provider(), build_audit_log())
        result = service.process(payload)
    except (OSError, json.JSONDecodeError, AccessOpsError) as exc:
        print(json.dumps({"outcome": "failure", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2

    print(json.dumps(result.safe_dict(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
