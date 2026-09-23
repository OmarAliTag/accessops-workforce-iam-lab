# Requirement-to-evidence and control matrix

This document keeps the portfolio claims specific and defensible.

## Deloitte role alignment

| Public role signal | Project evidence | What Omar can truthfully say | What this does not prove |
| --- | --- | --- | --- |
| IAM implementation and operation | `keycloak/accessops-realm.json`, `scripts/configure_realm.py`, live runbook | Configured and operated a local IAM learning environment | Production IAM platform ownership |
| OAuth, REST, and JSON | OIDC portal plus Keycloak Admin REST lifecycle adapter | Implemented an OIDC client and REST/JSON provisioning workflow | Enterprise federation programme delivery |
| Python scripting | `accessops/`, `scripts/`, tests | Wrote policy, lifecycle, evidence, and review automation | Large-scale production Python service ownership |
| Testing across scenarios | `tests/`, live positive/negative browser checks | Tested success, denial, validation failure, idempotency, and tamper detection | Formal enterprise test-lead experience |
| Troubleshooting auth/provisioning | Managed-attribute defect and documented recovery | Diagnosed a live provider read-back mismatch and fixed the realm schema | Breadth across every commercial IAM product |
| Containers | Optional `compose.yaml` plus pinned Keycloak image | Understands how the same realm can be mounted into the official image | A verified Docker run on the development PC |
| Knowledge transfer | Walkthrough, architecture, runbook, phone guide | Produced step-by-step technical handover documentation | Client training delivery under a formal engagement |
| IAM/PAM products | Keycloak lab; Okta migration map | Practised transferable IAM standards and lifecycle controls | SailPoint, Saviynt, ForgeRock, CyberArk, BeyondTrust, or Okta production experience |

## Implemented control objectives

| Control | Mechanism | Positive evidence | Negative evidence |
| --- | --- | --- | --- |
| Synthetic-data boundary | Joiners must use `@example.test` | Nadia accepted | Real domain rejected in tests |
| Approval separation | Requester and approver must differ | Three approved JML events | Self-approval sample returns failure |
| Least-privilege baseline | Department → groups → roles | Helpdesk can read tickets | Helpdesk receives 403 on IAM admin |
| Separation of duties | Requester and approver groups cannot coexist | Valid Finance Requesting baseline | Combined Finance groups blocked in tests |
| Mover cleanup | Remove current managed groups before adding destination groups | Finance role absent after Operations move | Wrong source department is rejected |
| Leaver containment | Remove groups, disable user, revoke sessions | Nadia reads back disabled with zero roles/groups | A second non-idempotent disable is rejected |
| Privileged hygiene | IAM group adds admin/auditor; TOTP required action | Access review flags pending TOTP | Privileged identity is not presented as compliant until enrollment |
| Safe retries | Event ID + canonical request hash | Same joiner event returns `replayed: true` | Same event ID with changed payload is rejected |
| Evidence integrity | Per-row hash + previous-row hash | `verify_audit.py` returns valid | Tampering test returns hash failure |
| Secret hygiene | Generated `.env`; audit redaction; ignored live evidence | Repository secret scan | Password/token/secret fields redact in tests |

## Verification boundaries

The closest boundary is used for each claim:

- **Provider state:** read back from Keycloak Admin REST.
- **Effective access:** visible ALLOW/403 route result after real OIDC login.
- **Automation:** result plus provider read-back plus audit event.
- **Evidence integrity:** independent recalculation of the full hash chain.
- **Repository quality:** tests, lint, ignored secrets, and live GitHub read-back.

