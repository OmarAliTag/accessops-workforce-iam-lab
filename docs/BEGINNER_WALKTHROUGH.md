# Beginner walkthrough: build, run, understand, and explain AccessOps

This is the hand-holding guide. Do not rush it. The goal is not only to make the lab run; it is to understand what each action changes, why that control exists, and what evidence proves it worked.

Use three PowerShell terminals:

- **Terminal A — Identity provider:** Keycloak stays running.
- **Terminal B — Application:** the Flask portal stays running.
- **Terminal C — Operator:** configuration, lifecycle, review, and tests.

## Before you start: the five-part mental model

1. **Identity** answers “Who is this user?” Keycloak owns the user record and login.
2. **Authentication** answers “Did they prove who they are?” Keycloak performs password/TOTP and OIDC.
3. **Authorization** answers “What may they do?” Groups grant roles; portal routes check roles.
4. **Lifecycle** answers “How should access change when the job changes?” Python handles joiner, mover, and leaver requests.
5. **Governance** answers “Can we explain and review the decision?” Tickets, approval separation, access reports, and audit records provide evidence.

---

## Step 1 — Inspect the project before running it

**Action**

Open these files in this order:

1. `keycloak/accessops-realm.json`
2. `accessops/policy.py`
3. `accessops/lifecycle.py`
4. `accessops/providers.py`
5. `portal/app.py`

**How it works**

The realm defines identities, groups, roles, OIDC clients, events, and the automation service account. The Python files then separate policy, workflow, provider calls, and application access checks.

**Why this action exists**

A good IAM engineer understands the intended control before applying configuration. Reading from policy to implementation makes the change explainable.

**Purpose**

Build a map in your head before handling errors.

**Expected evidence**

You can answer these questions:

- Which group gives `ticket-reader`?
- Why can a Finance requester not also be a Finance approver?
- Why does a mover remove groups before adding groups?
- Why is the portal read-only for lifecycle changes?

**Recovery if unclear**

Read [architecture](ARCHITECTURE.md), then return to the five files.

---

## Step 2 — Create an isolated Python environment

**Action**

From the project root, run:

```powershell
.\scripts\setup-python.ps1
```

**How it works**

The script selects the bundled Codex Python when present, otherwise the system Python. It creates `.venv`, installs pinned packages from `requirements-dev.txt`, copies `.env.example` to the ignored `.env`, and replaces placeholder secrets with cryptographically random local values.

**Why this action exists**

An isolated environment prevents project dependencies from changing the global Python installation. Generated secrets keep real values out of Git.

**Purpose**

Make setup reproducible and protect the host environment.

**Expected evidence**

The last lines say:

```text
Local .env ready. Generated values are intentionally not printed or committed.
Python environment ready: ...\.venv\Scripts\python.exe
```

**Recovery**

- `python not found`: install Python 3.11+ or update `$bundledPython` in the setup script.
- package download fails: verify internet access, then rerun; pip safely reuses installed packages.
- `.env` still has `replace-...`: run `.\.venv\Scripts\python.exe .\scripts\bootstrap_env.py`.

---

## Step 3 — Install and verify Keycloak

**Action**

```powershell
.\scripts\install-keycloak.ps1
```

**How it works**

The script downloads the official Keycloak 26.7.4 ZIP into `%USERPROFILE%\.cache\accessops-runtime`, calculates SHA-256, compares it with the pinned GitHub release digest, extracts only after a match, and runs `kc.bat --version`.

**Why this action exists**

Version pinning makes the lab predictable. Checksum validation prevents a corrupt or different archive from being trusted silently.

**Purpose**

Provide a real identity provider without requiring Docker or a paid tenant.

**Expected evidence**

```text
Keycloak 26.7.4
JVM: 17...
KEYCLOAK_HOME=...\keycloak-26.7.4
```

**Recovery**

- checksum mismatch: stop. Remove only the downloaded ZIP after checking the exact path, then download again from the official release.
- Java missing: install a supported OpenJDK. Keycloak's support matrix includes OpenJDK 17, 21, and 25 for this version.
- `JAVA_HOME` warning: the lab may still run through `java` on `PATH`; set `JAVA_HOME` later for a cleaner workstation setup.

---

## Step 4 — Start the identity provider

**Action — Terminal A**

```powershell
.\scripts\start-keycloak.ps1
```

Keep Terminal A open.

**How it works**

The script loads ignored values from `.env`, maps them to Keycloak's bootstrap and realm-import variables, copies the realm file into Keycloak's startup import directory, and binds development mode to `127.0.0.1:8080`.

**Why this action exists**

The realm must be online before the portal can discover OIDC endpoints or automation can call Admin REST.

**Purpose**

Create one reproducible identity control plane.

**Expected evidence**

Wait until Terminal A shows:

```text
Realm 'accessops' imported
Keycloak 26.7.4 ... Listening on: http://127.0.0.1:8080
```

Then visit:

`http://127.0.0.1:8080/realms/accessops/.well-known/openid-configuration`

You should see JSON with an issuer ending in `/realms/accessops`.

**Recovery**

- port 8080 in use: use the runbook's port check; do not kill an unknown process.
- `Realm already exists`: normal on restart. Startup import intentionally preserves current state.
- start-dev warning: expected and important. This lab is not production.

---

## Step 5 — Configure managed identity attributes

**Action — Terminal C**

```powershell
.\.venv\Scripts\python.exe .\scripts\configure_realm.py
```

**How it works**

The script uses the bootstrap administrator once to add administrator-only `department` and `data_classification` attributes to Keycloak's user-profile schema. It restores those values for imported synthetic users and independently proves that the automation service account can query users.

**Why this action exists**

Keycloak ignores undeclared custom attributes by default. A successful user-create response is not proof that `department` persisted.

**Purpose**

Make department a controlled, validated identity attribute and close a common provisioning/read-back gap.

**Expected evidence**

```json
{
  "managed_attributes": ["data_classification", "department"],
  "service_account_verified": true
}
```

**Recovery**

- connection error: confirm Terminal A is still running.
- HTTP 401: rerun `bootstrap_env.py` only if `.env` still has placeholders; otherwise check that the realm was created with the same `.env` values.
- department is blank later: rerun this step, then read the user through Admin REST before continuing.

---

## Step 6 — Start the OIDC-protected portal

**Action — Terminal B**

```powershell
.\scripts\start-portal.ps1
```

Keep Terminal B open, then visit `http://127.0.0.1:5000`.

**How it works**

Flask reads Keycloak's discovery document, redirects the browser to Keycloak, validates the authorization-code response through Authlib, saves only safe identity claims in an HTTP-only session cookie, and enforces roles at each protected route.

**Why this action exists**

An IAM project should prove effective access, not only show users and roles in an admin console.

**Purpose**

Demonstrate authentication and authorization at an application boundary.

**Expected evidence**

The landing page shows the AccessOps control flow. `http://127.0.0.1:5000/health` returns `status: ok` and the audit-chain result.

**Recovery**

- startup refuses placeholders: run Step 2 again.
- discovery error: open Keycloak's well-known URL and compare `OIDC_ISSUER` in `.env`.
- redirect mismatch: confirm the browser uses `127.0.0.1`, not an unrelated host name.

---

## Step 7 — Prove login, allow, and deny

**Action**

1. Click **Sign in with Keycloak**.
2. Use the fictional `nour.helpdesk` account and the local-only password in `keycloak/accessops-realm.json`.
3. Open **Helpdesk tickets**.
4. Try **IAM administration**.

**How it works**

Nour belongs to `Employees` and `Helpdesk`. Those groups grant `portal-user` and `ticket-reader`. Nour does not receive `iam-admin`.

**Why this action exists**

The allowed page proves the required role works. The 403 proves authentication alone does not bypass authorization.

**Purpose**

Show least privilege with one easy before/after contrast.

**Expected evidence**

- Dashboard: Nour's username, synthetic email, immutable Keycloak subject ID, and two roles.
- Tickets: visible `DECISION ALLOW` and a synthetic table.
- IAM admin: visible `AUTHORIZATION RESULT / 403`.
- Audit log: `authentication.login` and `authorization.denied` events.

**Recovery**

- invalid password: copy only the synthetic value from the realm file; never substitute a real password.
- no roles on dashboard: inspect the OIDC realm-role protocol mapper in the portal client.
- IAM admin unexpectedly opens: stop the demo and inspect Nour's current groups in Keycloak.

---

## Step 8 — Prove a rejected request

**Action — Terminal C**

```powershell
.\.venv\Scripts\python.exe .\scripts\lifecycle.py .\requests\04-rejected-self-approval.json
```

**How it works**

The policy layer compares `requested_by` and `approved_by` before calling Keycloak.

**Why this action exists**

A polished IAM project shows failure controls, not only the happy path.

**Purpose**

Demonstrate separation of duties and fail-closed behavior.

**Expected evidence**

```json
{
  "outcome": "failure",
  "error": "The requester cannot approve their own access change."
}
```

`blocked.example` must not appear in Keycloak. The failure itself is audited safely.

**Recovery**

This is an expected exit code of 2. Do not “fix” the request by making up a second approver; use a real approved sample instead.

---

## Step 9 — Run the joiner

**Action**

```powershell
.\.venv\Scripts\python.exe .\scripts\lifecycle.py .\requests\01-joiner.json
```

**How it works**

The service validates the request, proves the event ID is new, creates Nadia, sets a temporary password, assigns `Employees` and `Finance-Requesters`, and reads the identity back.

**Why this action exists**

New starters should receive a predictable baseline, not ad-hoc entitlements.

**Purpose**

Demonstrate automated least-privilege onboarding.

**Expected evidence**

- `enabled: true`
- `department: Finance Requesting`
- roles contain `finance-requester` and `portal-user`
- `required_actions` contains `UPDATE_PASSWORD`

Run the exact command again. It should say `replayed: true` and must not create a second user.

**Recovery**

- identity already exists with no matching success event: investigate; do not auto-adopt an unknown record.
- department blank: stop and return to Step 5.

---

## Step 10 — Run the mover

**Action**

```powershell
.\.venv\Scripts\python.exe .\scripts\lifecycle.py .\requests\02-mover.json
```

**How it works**

The service verifies Nadia currently belongs to Finance Requesting, removes the Finance managed group, adds Operations, updates department, and reads the user back.

**Why this action exists**

Access accumulation during transfers is a common identity risk.

**Purpose**

Prove that old access disappears before replacement access appears.

**Expected evidence**

- the identity ID is unchanged;
- `finance-requester` is absent;
- `operations-user` is present;
- groups are exactly `Employees` and `Operations`.

**Recovery**

If the current department does not match the request, the workflow fails. Correct the source system or request; do not force the move.

---

## Step 11 — Run the leaver

**Action**

```powershell
.\.venv\Scripts\python.exe .\scripts\lifecycle.py .\requests\03-leaver.json
```

**How it works**

The service removes every lab-managed group, disables the Keycloak identity, calls the logout endpoint to revoke sessions, and reads the final state back.

**Why this action exists**

Removing roles without disabling the identity can leave other paths open. Disabling without revoking sessions can leave existing sessions active.

**Purpose**

Demonstrate complete offboarding containment.

**Expected evidence**

- `enabled: false`
- empty `groups`
- empty `roles`
- same immutable identity ID as joiner and mover

**Recovery**

If the provider result is ambiguous, do not rerun blindly. Query the identity first, preserve the audit evidence, then decide whether a safe retry is needed.

---

## Step 12 — Generate governance evidence

**Action**

```powershell
.\.venv\Scripts\python.exe .\scripts\access_review.py
.\.venv\Scripts\python.exe .\scripts\verify_audit.py
```

**How it works**

The review reads current identities, groups, roles, privilege status, required actions, and exceptions. Audit verification recalculates every row hash and link from `GENESIS` to the last event.

**Why this action exists**

Configuration is not governance until somebody can review who has access and trace why it changed.

**Purpose**

Create clear evidence for an access-certification conversation.

**Expected evidence**

- `evidence/access-review.csv`
- `evidence/access-review.json`
- `valid: true` from audit verification
- Dina flagged until privileged TOTP enrollment is complete

**Recovery**

- audit chain invalid: preserve the file, stop relying on it, identify the first failed record, and regenerate only from an authoritative source. Do not edit hashes manually.
- exception count nonzero: read the exact reason. An exception is a review prompt, not automatically a software error.

---

## Step 13 — Run automated tests and lint

**Action**

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check . --exclude .venv
```

**How it works**

Tests use an isolated fake provider to exercise policy and lifecycle invariants without modifying Keycloak. Portal tests inject safe sessions to verify allow/deny behavior. Lint catches code-quality issues.

**Why this action exists**

Manual demos prove one path. Automated tests prevent a later change from quietly breaking controls.

**Purpose**

Demonstrate SDLC and verification discipline.

**Expected evidence**

All tests pass and Ruff reports `All checks passed!`.

**Recovery**

Read the first failure, fix its cause, and rerun the narrow test before the full suite. Do not weaken a control assertion just to make a test green.

---

## Step 14 — Prepare a fresh live demo without resetting the realm

The stable sample was designed for the first proof run. For a later interview demo, create a new synthetic identity automatically:

```powershell
.\.venv\Scripts\python.exe .\scripts\demo_scenario.py
```

The script pauses after joiner and mover so you can explain the role changes. It generates a unique username, ticket numbers, and event IDs, then ends by disabling that synthetic identity.

Use `--no-pause` only for a rapid verification run.

---

## Optional: container profile

`compose.yaml` maps the same realm into the official Keycloak image. It is included to show how the configuration moves into a container, but Docker was unavailable on the development PC, so the compose profile was not claimed as runtime-verified.

When Docker is available:

```powershell
docker compose up
```

Then continue at Step 5. Do not present this path as verified until the discovery endpoint, service account, OIDC login, lifecycle flow, and final state all pass again.

---

## What you should be able to explain at the end

- Why identity lifecycle is more than a login screen.
- The difference between Keycloak groups and application roles.
- Why the mover removes before adding.
- Why a disabled leaver also needs session revocation.
- Why idempotency matters in automation.
- Why provider read-back is stronger than a successful HTTP response.
- Why the audit hash chain is useful but not equivalent to immutable SIEM storage.
- Which parts are transferable to Okta/SailPoint/CyberArk and which product claims you are not making.

