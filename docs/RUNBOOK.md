# Operations, troubleshooting, and hyper-care runbook

## Service map

| Service | URL | Healthy signal |
| --- | --- | --- |
| Keycloak discovery | `http://127.0.0.1:8080/realms/accessops/.well-known/openid-configuration` | JSON issuer is the AccessOps realm |
| Keycloak admin console | `http://127.0.0.1:8080/admin/` | Login page renders |
| Portal | `http://127.0.0.1:5000/` | AccessOps landing page renders |
| Portal health | `http://127.0.0.1:5000/health` | `status: ok`; audit-chain status included |

## Start order

1. Keycloak.
2. Realm configuration.
3. Portal.
4. Lifecycle/review commands.

The reverse order produces discovery or connection failures and should not be treated as a product defect.

## Symptom: port 8080 or 5000 is already in use

**Check**

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8080,5000 |
    Select-Object LocalAddress,LocalPort,OwningProcess
```

**Why**

Starting a second instance can target the wrong realm or overwrite the wrong logs.

**Recovery**

Identify the owning process. Stop only an AccessOps process that you started and have positively identified. Never kill an unknown process merely to free a port.

## Symptom: Keycloak starts but the AccessOps realm is missing

**Check**

- The import file exists at `keycloak/accessops-realm.json`.
- Terminal A includes `Realm 'accessops' imported` on the first run.
- The runtime import directory contains `accessops-realm.json`.

**Cause**

Startup import reads only JSON files in Keycloak's `data/import` directory. Existing realms are skipped intentionally.

**Recovery**

Rerun `start-keycloak.ps1` after confirming the script's exact `KeycloakHome`. Do not overwrite or delete an existing realm until its state and evidence are understood.

## Symptom: service-account authentication fails

**Check**

```powershell
.\.venv\Scripts\python.exe .\scripts\configure_realm.py
```

**Likely causes**

- `.env` changed after the realm was imported.
- the realm already existed with an older client secret.
- the service-account role mappings were removed.

**Recovery**

Compare the current realm client with the intended import. For a clean learning reset, preserve `evidence/` first and create a separate fresh Keycloak runtime rather than deleting an unknown data directory.

## Symptom: user is created but `department` is blank

**Cause**

Keycloak ignored a custom attribute not defined in the user-profile schema.

**Recovery**

Run `configure_realm.py`, confirm both managed attributes read back, then query the user again. Do not continue to a mover when the authoritative source department is blank.

## Symptom: OIDC login returns redirect or state errors

**Checks**

- Portal URL is `http://127.0.0.1:5000`.
- `.env` issuer is `http://127.0.0.1:8080/realms/accessops`.
- Keycloak client redirect URI is `http://127.0.0.1:5000/auth/callback`.
- The browser did not reuse a callback from an earlier portal restart.

**Recovery**

Start from the portal home page and initiate a new login. Do not edit the returned OAuth `state` or authorization code.

## Symptom: login works but roles are missing

**Checks**

- The user belongs to the expected Keycloak groups.
- The group has the expected realm-role mapping.
- The portal client includes the realm-role OIDC mapper.
- The ID/userinfo token has `realm_access.roles`.

**Recovery**

Fix the earliest missing mapping and sign in again to obtain a new token. Existing tokens do not retroactively change.

## Symptom: an allowed page returns 403

**Check**

Read the dashboard's effective roles, then inspect the route's decorator in `portal/app.py`.

**Recovery**

Correct the identity group or role mapping, not the application check, unless the business policy itself is wrong.

## Symptom: an unauthorized page opens

**Severity**

Treat this as a security defect.

**Actions**

1. Stop the demo.
2. Preserve the token claims, route, user groups, and audit evidence without exposing secrets.
3. Reproduce with an automated negative test.
4. Fix the mapping or decorator.
5. Verify both ALLOW and DENY boundaries again.

## Symptom: lifecycle command returns a provider error

**Actions**

1. Do not rerun blindly.
2. Query the user through Admin REST.
3. Compare current state with the requested transition.
4. Inspect the last audit failure.
5. Retry only when the request is idempotent and the authoritative state shows it is safe.

## Symptom: audit verification fails

**Actions**

1. Preserve the original file.
2. Note `failed_record` and `reason`.
3. Stop using the log as verified evidence.
4. Reconcile against Keycloak state and terminal output.
5. Regenerate evidence through normal actions; never hand-edit hashes.

## Hyper-care checklist after a change

- Discovery endpoint responds.
- Portal health is `ok`.
- One approved identity can sign in.
- One permitted route returns ALLOW.
- One prohibited route returns 403.
- Automation service account can read users.
- A safe access review completes.
- Audit chain is valid.
- Automated tests and lint pass.
- No `.env`, tokens, runtime database, or live audit log are staged for Git.

