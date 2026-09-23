from __future__ import annotations

import secrets
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
EXAMPLE_PATH = PROJECT_ROOT / ".env.example"


def generated_values() -> dict[str, str]:
    return {
        "FLASK_SECRET_KEY": secrets.token_urlsafe(36),
        "OIDC_CLIENT_SECRET": secrets.token_urlsafe(36),
        "KEYCLOAK_AUTOMATION_CLIENT_SECRET": secrets.token_urlsafe(36),
        "KEYCLOAK_BOOTSTRAP_PASSWORD": secrets.token_urlsafe(36),
        "JOINER_TEMPORARY_PASSWORD": f"AccessOps-Temp-{secrets.token_urlsafe(18)}!",
    }


def main() -> int:
    if not ENV_PATH.exists():
        ENV_PATH.write_text(EXAMPLE_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    replacements = generated_values()
    changed: list[str] = []
    output: list[str] = []
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            output.append(line)
            continue
        key, value = line.split("=", 1)
        if key in replacements and value.startswith(("replace-", "Replace-")):
            output.append(f"{key}={replacements[key]}")
            changed.append(key)
        else:
            output.append(line)
    ENV_PATH.write_text("\n".join(output) + "\n", encoding="utf-8")

    print("Local .env ready. Generated values are intentionally not printed or committed.")
    print("Configured keys: " + (", ".join(sorted(changed)) if changed else "already configured"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
