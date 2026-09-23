# Verification report

Date: 23 September 2026

Environment: Windows 11, Python 3.12.14, Java 17.0.7, Keycloak 26.7.4

Data classification: synthetic local lab data only

## Result

The primary bare-metal Keycloak path passed. The optional Docker Compose path was not executed because Docker was not installed on this workstation and is not claimed as verified.

## Provider boundary

- Official Keycloak release archive size: 176,717,726 bytes.
- Downloaded archive SHA-256 matched the GitHub release digest: `a286e98b4296d4e75ee88d8527c7cd463b307caa022f088c9f22cffccc741fa1`.
- Keycloak 26.7.4 started on JVM 17 and listened on `127.0.0.1:8080`.
- Startup log reported `Realm 'accessops' imported` and `Import finished successfully`.
- OIDC discovery issuer read back as `http://127.0.0.1:8080/realms/accessops`.
- Realm configuration read back both `department` and `data_classification` as managed attributes.
- The `accessops-automation` service account authenticated and queried users.

## Lifecycle boundary

- Deliberate self-approval: rejected; no `blocked.example` identity created.
- Joiner: Nadia created enabled in Finance Requesting with `Employees` and `Finance-Requesters`.
- Idempotency: exact joiner replay returned `replayed: true`; no duplicate created.
- Mover: immutable identity ID preserved; Finance role removed; Operations role added.
- Leaver: same identity read back disabled with zero managed groups and zero effective lab roles; logout/session-revocation endpoint succeeded.
- Final canonical Nadia identity ID: `fbcdef58-5a82-4d1f-92ab-2acc91c7fe12` in the local disposable realm only.
- The fresh guided-demo command independently completed all three stages for a second unique synthetic identity without resetting the realm.

## Application boundary

- Portal home returned HTTP 200 and a restrictive Content Security Policy.
- OIDC authorization-code flow reached Keycloak and returned to the portal dashboard.
- Nour's dashboard showed the signed subject plus `portal-user` and `ticket-reader`.
- Helpdesk route displayed `DECISION ALLOW`.
- IAM administration displayed `AUTHORIZATION RESULT / 403`.
- The denial appeared in the audit evidence.

## Evidence boundary

- Final access review completed with four identities after the canonical and guided-demo runs.
- Two identities remained enabled; both Nadia identities were disabled.
- One intentional exception remained: privileged TOTP enrollment pending for Dina.
- The four-record canonical lifecycle audit chain verified as valid immediately after JML. Browser login/denial and guided-demo events appended later; the final nine-record chain remained valid.
- Audit tests proved secret-field redaction and tamper detection.

## Automated quality boundary

- Pytest: 21 passed after documentation and artifact checks were added.
- Ruff: all checks passed after final formatting.
- The final clean-state test, lint, secret scan, repository scan, and public GitHub read-back are recorded in the delivery handoff after the commit is published.
