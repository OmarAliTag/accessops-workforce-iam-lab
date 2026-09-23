import pytest

from accessops.exceptions import PolicyViolation, ValidationError
from accessops.policy import roles_for_groups, validate_change_request, validate_group_set


def valid_joiner() -> dict[str, str]:
    return {
        "event_id": "EVT-TEST-1001",
        "action": "joiner",
        "ticket_id": "IAM-9001",
        "requested_by": "hr.partner",
        "approved_by": "finance.manager",
        "reason": "Approved synthetic onboarding request.",
        "username": "nadia.hassan",
        "first_name": "Nadia",
        "last_name": "Hassan",
        "email": "nadia.hassan@example.test",
        "department": "Finance Requesting",
    }


def test_valid_joiner_is_normalized() -> None:
    normalized = validate_change_request(valid_joiner())
    assert normalized["username"] == "nadia.hassan"
    assert normalized["department"] == "Finance Requesting"


def test_self_approval_is_blocked() -> None:
    request = valid_joiner()
    request["approved_by"] = request["requested_by"]
    with pytest.raises(PolicyViolation, match="cannot approve"):
        validate_change_request(request)


def test_real_email_domain_is_blocked() -> None:
    request = valid_joiner()
    request["email"] = "nadia@real-company.com"
    with pytest.raises(PolicyViolation, match="synthetic"):
        validate_change_request(request)


def test_unknown_department_is_blocked() -> None:
    request = valid_joiner()
    request["department"] = "Executive Override"
    with pytest.raises(ValidationError, match="Unknown department"):
        validate_change_request(request)


def test_separation_of_duties_conflict_is_blocked() -> None:
    with pytest.raises(PolicyViolation, match="Separation-of-duties"):
        validate_group_set(("Employees", "Finance-Requesters", "Finance-Approvers"))


def test_roles_are_derived_from_groups() -> None:
    assert roles_for_groups(("Employees", "Helpdesk")) == ("portal-user", "ticket-reader")
