from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from accessops.exceptions import AccessOpsError  # noqa: E402
from accessops.review import write_review  # noqa: E402
from scripts.common import build_provider  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a point-in-time IAM access review.")
    parser.add_argument(
        "--csv",
        type=Path,
        default=PROJECT_ROOT / "evidence" / "access-review.csv",
        help="CSV output path",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=PROJECT_ROOT / "evidence" / "access-review.json",
        help="JSON output path",
    )
    args = parser.parse_args()
    try:
        report = write_review(build_provider(), args.csv, args.json)
    except (OSError, AccessOpsError) as exc:
        print(json.dumps({"outcome": "failure", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
