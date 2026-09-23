from __future__ import annotations

import re
from typing import Any

from .exceptions import PolicyViolation, ValidationError

DEPARTMENT_GROUPS: dict[str, tuple[str, ...]] = {
    "Helpdesk": ("Employees", "Helpdesk"),
    "IAM Operations": ("Employees", "IAM-Operations"),
    "Finance Requesting": ("Employees", "Finance-Requesters"),
    "Finance Approval": ("Employees", "Finance-Approvers"),
    "Operations": ("Employees", "Operations"),
}

GROUP_ROLES: dict[str, tuple[str, ...]] = {
    "Employees": ("portal-user",),
    "Helpdesk": ("ticket-reader",),
    "IAM-Operations": ("iam-admin", "auditor"),
    "Finance-Requesters": ("finance-requester",),
    "Finance-Approvers": ("finance-approver",),
    "Operations": ("operations-user",),
}

MANAGED_GROUPS = frozenset(GROUP_ROLES)
PRIVILEGED_ROLES = frozenset({"iam-admin", "auditor"})
SOD_CONFLICT = frozenset({"Finance-Requesters", "Finance-Approvers"})

_USERNAME = re.compile(r"^[a-z][a-z0-9._-]{2,31}$")
_TICKET = re.compile(r"^IAM-[0-9]{4,}$")
_EVENT = re.compile(r"^EVT-[A-Z0-9-]{4,40}$")


def groups_for_department(department: str) -> tuple[str, ...]:
    try:
        return DEPARTMENT_GROUPS[department]
    except KeyError as exc:
        allowed = ", ".join(sorted(DEPARTMENT_GROUPS))
        raise ValidationError(f"Unknown department '{department}'. Allowed: {allowed}") from exc


def roles_for_groups(groups: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    roles = {role for group in groups for role in GROUP_ROLES.get(group, ())}
    return tuple(sorted(roles))


def validate_group_set(groups: list[str] | tuple[str, ...]) -> None:
    selected = set(groups)
    if SOD_CONFLICT.issubset(selected):
        raise PolicyViolation(
            "Separation-of-duties policy blocks Finance-Requesters and Finance-Approvers on the same identity."
        )


def _required_text(payload: dict[str, Any], key: str, *, minimum: int = 1) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or len(value.strip()) < minimum:
        raise ValidationError(f"'{key}' is required and must contain at least {minimum} characters.")
    value = value.strip()
    if len(value) > 160:
        raise ValidationError(f"'{key}' is too long for this lab.")
    if any(ord(char) < 32 for char in value):
        raise ValidationError(f"'{key}' contains unsupported control characters.")
    return value


def validate_change_request(payload: dict[str, Any]) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise ValidationError("The request must be a JSON object.")

    action = _required_text(payload, "action").lower()
    if action not in {"joiner", "mover", "leaver"}:
        raise ValidationError("'action' must be joiner, mover, or leaver.")

    normalized = {
        "event_id": _required_text(payload, "event_id"),
        "action": action,
        "ticket_id": _required_text(payload, "ticket_id"),
        "requested_by": _required_text(payload, "requested_by"),
        "approved_by": _required_text(payload, "approved_by"),
        "reason": _required_text(payload, "reason", minimum=8),
        "username": _required_text(payload, "username").lower(),
    }

    if not _EVENT.fullmatch(normalized["event_id"]):
        raise ValidationError("'event_id' must look like EVT-DEMO-1001.")
    if not _TICKET.fullmatch(normalized["ticket_id"]):
        raise ValidationError("'ticket_id' must look like IAM-1001.")
    if not _USERNAME.fullmatch(normalized["username"]):
        raise ValidationError("'username' must be 3-32 lowercase letters, digits, dots, dashes, or underscores.")
    if normalized["requested_by"].casefold() == normalized["approved_by"].casefold():
        raise PolicyViolation("The requester cannot approve their own access change.")

    if action == "joiner":
        normalized.update(
            {
                "first_name": _required_text(payload, "first_name"),
                "last_name": _required_text(payload, "last_name"),
                "email": _required_text(payload, "email").lower(),
                "department": _required_text(payload, "department"),
            }
        )
        if not normalized["email"].endswith("@example.test"):
            raise PolicyViolation("Only synthetic @example.test identities are allowed in this lab.")
        validate_group_set(groups_for_department(normalized["department"]))

    elif action == "mover":
        normalized.update(
            {
                "from_department": _required_text(payload, "from_department"),
                "to_department": _required_text(payload, "to_department"),
            }
        )
        if normalized["from_department"] == normalized["to_department"]:
            raise ValidationError("A mover request must change the department.")
        groups_for_department(normalized["from_department"])
        validate_group_set(groups_for_department(normalized["to_department"]))

    return normalized
