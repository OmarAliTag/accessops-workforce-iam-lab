# Research and stack-selection record

Research used official employer, product, and standards documentation available on 23 September 2026.

## Deloitte signals used

- [Deloitte Innovation Hub — Identity and Access Management Engineer, requisition 253425](https://middleeastjobs.deloitte.com/careersME/PipelineDetail/Egypt-Deloitte-Innovation-Hub-I-Cyber-Security-I-Identity-and-Access-Management-Engineer-Cairo-Egypt/253425)
  - Public role signals used: IAM implementation/configuration, integrations, testing, troubleshooting, production support, knowledge transfer, OAuth, REST/JSON, Python, Docker/Kubernetes, and named IAM/PAM technologies.
- [Digital Identity by Deloitte](https://www.deloitte.com/global/en/services/risk-advisory/services/digital-identity-by-deloitte.html)
  - Hire-to-Retire lifecycle, access management, SSO/MFA, PAM/least privilege, audit, automation, metrics, and operations.
- [Deloitte Digital Identity Services](https://www.deloitte.com/us/en/services/consulting/services/digital-identity-services.html)
  - Access management, identity administration, role-based access control, governance, PAM, and alliance technologies including Okta.
- [Deloitte Cyber Identity](https://www.deloitte.com/us/en/services/consulting/services/cyber-identity.html)
  - Authentication, authorization, auditing, lifecycle provisioning, transfer/offboarding, certification, remediation, and monitoring.

## Keycloak primary sources

- [Downloads — version 26.7.4](https://www.keycloak.org/downloads)
- [ZIP quickstart](https://www.keycloak.org/getting-started/getting-started-zip)
- [Supported configurations](https://www.keycloak.org/server/supported-configurations)
- [Server Administration Guide](https://www.keycloak.org/docs/latest/server_admin/)
- [OpenID Connect layers](https://www.keycloak.org/securing-apps/oidc-layers)
- [Admin REST API](https://www.keycloak.org/docs-api/latest/rest-api/index.html)
- [Realm import/export and environment placeholders](https://www.keycloak.org/server/importExport)
- [Container guide](https://www.keycloak.org/server/containers)

## Okta primary sources

- [Integrator Free Plan defaults and limits](https://developer.okta.com/docs/reference/org-defaults/)
- [Python/Flask hosted-redirect example](https://developer.okta.com/docs/guides/sampleapp-oie-redirectauth/flask/main/)
- [App sign-in and MFA policy](https://developer.okta.com/docs/guides/configure-signon-policy/main/)
- [Hosted sign-in deployment choice](https://developer.okta.com/docs/guides/oie-choose-signin-deploy/main/)

## Options considered

### 1. Keycloak local lab — selected

**Strengths**

- free and reproducible;
- OIDC, roles/groups, TOTP, events, and Admin REST;
- direct Windows/Java or official container image;
- a reviewer can run it without a paid tenant.

**Risks**

- not one of the commercial products named in the role;
- development mode is not production;
- local H2 persistence and bootstrap administration need explicit limits.

**Mitigation**

Frame it as standards practice, include production next steps, and map it to Okta without claiming product ownership.

### 2. Okta Integrator Free Plan — phase two

**Strengths**

- explicitly named in the role and Deloitte alliance material;
- strong SSO, directory, MFA, lifecycle, OAuth/OIDC, and API story.

**Risks**

- signup requires an eligible unique business email and can be location/account dependent;
- external tenant availability would block a reproducible beginner walkthrough.

**Decision**

Keep the integration provider-neutral and add the migration plan, but do not make an unconfirmed tenant a prerequisite.

### 3. SailPoint/CyberArk-specific lab — not selected

**Strengths**

- close product-name match to the role.

**Risks**

- dependable public tenants and full lab access are not generally available;
- a mock would create weaker evidence and encourage overstated product claims.

## Inference: what should appeal to the hiring manager

This is an inference from the role and Deloitte service material, not a statement from Deloitte about this repository:

1. lead with the client/business problem;
2. show full lifecycle instead of only SSO;
3. prove least privilege through an actual allowed and denied resource;
4. test failures and troubleshoot provider behavior;
5. produce operational evidence and a runbook;
6. explain the solution clearly and disclose limitations.

