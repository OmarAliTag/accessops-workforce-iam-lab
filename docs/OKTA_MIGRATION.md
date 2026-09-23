# Phase two: provider-neutral migration to Okta

This is a design map, not a claim that the current repository has been executed against an Okta tenant.

## Why Okta is the next provider

Okta appears in the public role and Deloitte's identity-alliance material. A successful phase-two demo would add directly named technology experience while preserving the same lifecycle and control story.

## Concept mapping

| AccessOps / Keycloak | Okta equivalent | Migration note |
| --- | --- | --- |
| Realm | Okta org / authorization server | Replace `OIDC_ISSUER` and metadata |
| User profile attributes | Universal Directory profile attributes | Define `department` and data classification before provisioning |
| Groups | Okta groups | Keep business names and group-first assignment |
| Realm roles in token | Group or custom claims | Map allowed groups/roles into ID/access token claims |
| Confidential OIDC client | Okta OIDC web application | Use hosted redirect and exact callback URIs |
| Required action `CONFIGURE_TOTP` | App sign-in/authenticator enrollment policy | Require stronger policy for privileged group |
| Admin REST user lifecycle | Okta Users and Groups APIs | Implement the same provider contract |
| Keycloak events | Okta System Log | Export login, policy, and lifecycle evidence |
| Service-account client | OAuth 2.0 service app / scoped API access | Apply the least API scopes needed |

## Provider contract to preserve

The lifecycle layer should not change. An `OktaProvider` should implement:

- `get_user(username)`
- `list_users()`
- `create_user(...)`
- `move_user(username, department, groups)`
- `disable_user(username)`

Every method must return the same safe `Identity` model so policy, idempotency, audit, review, and tests remain provider-independent.

## Migration steps

1. Obtain an eligible Okta Integrator Free Plan org.
2. Create custom profile attributes before provisioning.
3. Create business groups matching the lab.
4. Create a hosted-redirect OIDC web application with local callback URLs.
5. Configure token group/role claims.
6. Create scoped automation credentials; do not reuse a human administrator session.
7. Implement `OktaProvider` against official APIs.
8. Run the existing provider contract and lifecycle test matrix.
9. Re-run browser ALLOW and 403 evidence.
10. Capture System Log and access-review evidence.
11. Update the phone explanation only after every boundary is verified.

## Gate before claiming Okta experience

Do not add Okta to the project headline or CV until all of these are true:

- real tenant and app exist;
- OIDC login succeeds;
- group/role claim is visible and enforced;
- joiner, mover, and leaver API actions read back correctly;
- MFA policy is enforced for the privileged identity;
- failures and retries behave safely;
- evidence contains no tenant secret, token, or real user data.

