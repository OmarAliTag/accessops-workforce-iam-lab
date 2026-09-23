from pathlib import Path

import pytest

from accessops.audit import AuditLog
from accessops.exceptions import IdempotencyConflict, IdentityConflict, PolicyViolation
from accessops.lifecycle import LifecycleService
from tests.fakes import FakeIdentityProvider


def joiner(event_id: str = "EVT-TEST-2001") -> dict[str, str]:
    return {
        "event_id": event_id,
        "action": "joiner",
        "ticket_id": "IAM-9101",
        "requested_by": "hr.partner",
        "approved_by": "finance.manager",
        "reason": "Approved synthetic onboarding request.",
        "username": "nadia.hassan",
        "first_name": "Nadia",
        "last_name": "Hassan",
        "email": "nadia.hassan@example.test",
        "department": "Finance Requesting",
    }


def service(tmp_path: Path) -> tuple[LifecycleService, FakeIdentityProvider, AuditLog]:
    provider = FakeIdentityProvider()
    audit = AuditLog(tmp_path / "audit.jsonl")
    return LifecycleService(provider, audit), provider, audit


def test_full_joiner_mover_leaver_lifecycle(tmp_path: Path) -> None:
    lifecycle, provider, audit = service(tmp_path)
    created = lifecycle.process(joiner())
    assert created.identity.enabled is True
    assert created.identity.groups == ("Employees", "Finance-Requesters")
    assert created.identity.roles == ("finance-requester", "portal-user")

    moved = lifecycle.process(
        {
            "event_id": "EVT-TEST-2002",
            "action": "mover",
            "ticket_id": "IAM-9102",
            "requested_by": "operations.manager",
            "approved_by": "iam.reviewer",
            "reason": "Approved move to Operations.",
            "username": "nadia.hassan",
            "from_department": "Finance Requesting",
            "to_department": "Operations",
        }
    )
    assert moved.identity.id == created.identity.id
    assert moved.identity.groups == ("Employees", "Operations")
    assert "finance-requester" not in moved.identity.roles
    assert moved.identity.roles == ("operations-user", "portal-user")

    left = lifecycle.process(
        {
            "event_id": "EVT-TEST-2003",
            "action": "leaver",
            "ticket_id": "IAM-9103",
            "requested_by": "hr.partner",
            "approved_by": "iam.reviewer",
            "reason": "Employment ended; remove access.",
            "username": "nadia.hassan",
        }
    )
    assert left.identity.enabled is False
    assert left.identity.groups == ()
    assert left.identity.roles == ()
    assert provider.create_calls == provider.move_calls == provider.disable_calls == 1
    assert audit.verify_chain() == {"valid": True, "records": 3, "failed_record": None, "reason": None}


def test_same_event_is_idempotent(tmp_path: Path) -> None:
    lifecycle, provider, _ = service(tmp_path)
    first = lifecycle.process(joiner())
    second = lifecycle.process(joiner())
    assert first.replayed is False
    assert second.replayed is True
    assert provider.create_calls == 1


def test_reused_event_with_different_body_is_rejected(tmp_path: Path) -> None:
    lifecycle, _, _ = service(tmp_path)
    lifecycle.process(joiner())
    changed = joiner()
    changed["reason"] = "Changed request body must not reuse an event identifier."
    with pytest.raises(IdempotencyConflict):
        lifecycle.process(changed)


def test_mover_checks_current_department(tmp_path: Path) -> None:
    lifecycle, _, audit = service(tmp_path)
    lifecycle.process(joiner())
    with pytest.raises(IdentityConflict, match="Keycloak shows"):
        lifecycle.process(
            {
                "event_id": "EVT-TEST-2010",
                "action": "mover",
                "ticket_id": "IAM-9110",
                "requested_by": "operations.manager",
                "approved_by": "iam.reviewer",
                "reason": "Incorrect source department should fail.",
                "username": "nadia.hassan",
                "from_department": "Helpdesk",
                "to_department": "Operations",
            }
        )
    assert audit.entries()[-1]["outcome"] == "failure"


def test_validation_failure_is_audited_without_mutation(tmp_path: Path) -> None:
    lifecycle, provider, audit = service(tmp_path)
    invalid = joiner("EVT-TEST-2020")
    invalid["approved_by"] = invalid["requested_by"]
    with pytest.raises(PolicyViolation):
        lifecycle.process(invalid)
    assert provider.users == {}
    event = audit.entries()[-1]
    assert event["action"] == "lifecycle.validation"
    assert event["outcome"] == "failure"
