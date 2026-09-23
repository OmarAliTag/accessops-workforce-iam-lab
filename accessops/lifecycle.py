from __future__ import annotations

from typing import Any

from .audit import AuditLog, request_hash
from .exceptions import IdempotencyConflict, IdentityConflict, IdentityNotFound
from .models import LifecycleResult
from .policy import groups_for_department, validate_change_request
from .providers import IdentityProvider


class LifecycleService:
    def __init__(self, provider: IdentityProvider, audit_log: AuditLog):
        self.provider = provider
        self.audit_log = audit_log

    def process(self, payload: dict[str, Any], *, actor: str = "accessops-automation") -> LifecycleResult:
        try:
            normalized = validate_change_request(payload)
        except Exception as exc:
            safe_payload = payload if isinstance(payload, dict) else {}
            source_event_id = str(safe_payload.get("event_id") or "EVT-INVALID")[:64]
            target = str(safe_payload.get("username") or "unknown")[:64]
            self.audit_log.append(
                source_event_id=source_event_id,
                action="lifecycle.validation",
                outcome="failure",
                actor=str(safe_payload.get("requested_by") or actor)[:64],
                target=target,
                request_digest=request_hash(safe_payload),
                summary={"error_type": type(exc).__name__, "error": str(exc)},
            )
            raise
        digest = request_hash(normalized)
        existing_events = self.audit_log.events_for(normalized["event_id"])

        if any(row.get("request_hash") != digest for row in existing_events):
            raise IdempotencyConflict(f"Event ID '{normalized['event_id']}' was already used with different data.")
        successful = [row for row in existing_events if row.get("outcome") == "success"]
        if successful:
            identity = self.provider.get_user(normalized["username"])
            if not identity:
                raise IdentityNotFound(
                    "The prior success is in the audit log, but the identity is missing from Keycloak."
                )
            return LifecycleResult(
                event_id=normalized["event_id"],
                action=normalized["action"],
                outcome="success",
                replayed=True,
                identity=identity,
                message="Idempotent replay: no duplicate change was made.",
            )

        before = self.provider.get_user(normalized["username"])
        try:
            if normalized["action"] == "joiner":
                if before:
                    raise IdentityConflict(f"Identity '{normalized['username']}' already exists.")
                after = self.provider.create_user(
                    username=normalized["username"],
                    email=normalized["email"],
                    first_name=normalized["first_name"],
                    last_name=normalized["last_name"],
                    department=normalized["department"],
                    groups=groups_for_department(normalized["department"]),
                )
                message = "Joiner created with the department's least-privilege access baseline."

            elif normalized["action"] == "mover":
                if not before:
                    raise IdentityNotFound(f"Identity '{normalized['username']}' was not found.")
                if before.department != normalized["from_department"]:
                    raise IdentityConflict(
                        f"Mover expected '{normalized['from_department']}', but Keycloak shows '{before.department}'."
                    )
                after = self.provider.move_user(
                    normalized["username"],
                    normalized["to_department"],
                    groups_for_department(normalized["to_department"]),
                )
                message = "Mover removed obsolete access before adding the new baseline."

            else:
                if not before:
                    raise IdentityNotFound(f"Identity '{normalized['username']}' was not found.")
                after = self.provider.disable_user(normalized["username"])
                message = "Leaver disabled; managed groups were removed and sessions were revoked."

            self.audit_log.append(
                source_event_id=normalized["event_id"],
                action=f"lifecycle.{normalized['action']}",
                outcome="success",
                actor=actor,
                target=normalized["username"],
                request_digest=digest,
                summary={
                    "ticket_id": normalized["ticket_id"],
                    "reason": normalized["reason"],
                    "approved_by": normalized["approved_by"],
                    "before": before.safe_dict() if before else None,
                    "after": after.safe_dict(),
                },
            )
            return LifecycleResult(
                event_id=normalized["event_id"],
                action=normalized["action"],
                outcome="success",
                replayed=False,
                identity=after,
                message=message,
            )
        except Exception as exc:
            self.audit_log.append(
                source_event_id=normalized["event_id"],
                action=f"lifecycle.{normalized['action']}",
                outcome="failure",
                actor=actor,
                target=normalized["username"],
                request_digest=digest,
                summary={
                    "ticket_id": normalized["ticket_id"],
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "before": before.safe_dict() if before else None,
                },
            )
            raise
