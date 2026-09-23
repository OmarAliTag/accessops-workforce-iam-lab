from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from accessops.audit import AuditLog, request_hash

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

LAB_ROLES = {
    "portal-user",
    "ticket-reader",
    "iam-admin",
    "auditor",
    "finance-requester",
    "finance-approver",
    "operations-user",
}


def _audit_path() -> Path:
    configured = Path(os.environ.get("ACCESSOPS_AUDIT_LOG", "evidence/audit-log.jsonl"))
    return configured if configured.is_absolute() else PROJECT_ROOT / configured


def _roles_from_claims(claims: dict[str, Any]) -> list[str]:
    realm_access = claims.get("realm_access") or {}
    roles = realm_access.get("roles") or claims.get("roles") or []
    return sorted({str(role) for role in roles if str(role) in LAB_ROLES})


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "replace-with-a-long-random-local-value"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,
        PERMANENT_SESSION_LIFETIME=900,
        OIDC_ISSUER=os.environ.get("OIDC_ISSUER", "http://127.0.0.1:8080/realms/accessops"),
        OIDC_CLIENT_ID=os.environ.get("OIDC_CLIENT_ID", "accessops-portal"),
        OIDC_CLIENT_SECRET=os.environ.get("OIDC_CLIENT_SECRET", ""),
    )
    if test_config:
        app.config.update(test_config)

    if not app.config["TESTING"] and (
        not app.config["SECRET_KEY"]
        or str(app.config["SECRET_KEY"]).startswith("replace-")
        or not app.config["OIDC_CLIENT_SECRET"]
        or str(app.config["OIDC_CLIENT_SECRET"]).startswith("replace-")
    ):
        raise RuntimeError("Replace FLASK_SECRET_KEY and OIDC_CLIENT_SECRET in .env before starting the portal.")

    audit_log = AuditLog(_audit_path())
    oauth = OAuth(app)
    oauth.register(
        name="keycloak",
        client_id=app.config["OIDC_CLIENT_ID"],
        client_secret=app.config["OIDC_CLIENT_SECRET"],
        server_metadata_url=f"{app.config['OIDC_ISSUER']}/.well-known/openid-configuration",
        client_kwargs={"scope": "openid profile email"},
    )

    def current_identity() -> dict[str, Any] | None:
        identity = session.get("identity")
        return identity if isinstance(identity, dict) else None

    def roles_required(*allowed_roles: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(view)
            def wrapped(*args: Any, **kwargs: Any) -> Any:
                identity = current_identity()
                if not identity:
                    return redirect(url_for("login", next=request.path))
                effective = set(identity.get("roles") or [])
                if not effective.intersection(allowed_roles):
                    source_id = f"WEB-DENY-{uuid.uuid4()}"
                    audit_log.append(
                        source_event_id=source_id,
                        action="authorization.denied",
                        outcome="failure",
                        actor=identity.get("username", "unknown"),
                        target=request.path,
                        request_digest=request_hash(
                            {"path": request.path, "roles": sorted(effective), "required": sorted(allowed_roles)}
                        ),
                        summary={"required_roles": sorted(allowed_roles), "effective_roles": sorted(effective)},
                    )
                    abort(403)
                return view(*args, **kwargs)

            return wrapped

        return decorator

    @app.context_processor
    def inject_identity() -> dict[str, Any]:
        return {"current_identity": current_identity()}

    @app.after_request
    def security_headers(response: Any) -> Any:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; img-src 'self' data:; "
            "script-src 'self'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def home() -> str:
        return render_template("home.html")

    @app.get("/login")
    def login() -> Any:
        callback = url_for("auth_callback", _external=True)
        return oauth.keycloak.authorize_redirect(callback)

    @app.get("/auth/callback")
    def auth_callback() -> Any:
        token = oauth.keycloak.authorize_access_token()
        claims = token.get("userinfo")
        if not isinstance(claims, dict):
            claims = oauth.keycloak.userinfo(token=token)
        identity = {
            "subject": claims.get("sub", ""),
            "username": claims.get("preferred_username", "unknown"),
            "name": claims.get("name", claims.get("preferred_username", "Unknown user")),
            "email": claims.get("email", ""),
            "roles": _roles_from_claims(dict(claims)),
        }
        session.clear()
        session["identity"] = identity
        session["id_token"] = token.get("id_token", "")
        session.permanent = True
        audit_log.append(
            source_event_id=f"WEB-LOGIN-{uuid.uuid4()}",
            action="authentication.login",
            outcome="success",
            actor=identity["username"],
            target="accessops-portal",
            request_digest=request_hash({"subject": identity["subject"], "roles": identity["roles"]}),
            summary={"roles": identity["roles"], "protocol": "OIDC authorization code"},
        )
        return redirect(url_for("dashboard"))

    @app.get("/logout")
    def logout() -> Any:
        id_token = session.get("id_token", "")
        identity = current_identity() or {}
        session.clear()
        metadata = oauth.keycloak.load_server_metadata()
        endpoint = metadata.get("end_session_endpoint")
        if not endpoint:
            return redirect(url_for("home"))
        params = {
            "post_logout_redirect_uri": url_for("home", _external=True),
            "client_id": app.config["OIDC_CLIENT_ID"],
        }
        if id_token:
            params["id_token_hint"] = id_token
        if identity:
            audit_log.append(
                source_event_id=f"WEB-LOGOUT-{uuid.uuid4()}",
                action="authentication.logout",
                outcome="success",
                actor=identity.get("username", "unknown"),
                target="accessops-portal",
                request_digest=request_hash({"subject": identity.get("subject", "")}),
                summary={"protocol": "OIDC RP-initiated logout"},
            )
        return redirect(f"{endpoint}?{urlencode(params)}")

    @app.get("/dashboard")
    @roles_required("portal-user")
    def dashboard() -> str:
        return render_template("dashboard.html", identity=current_identity())

    @app.get("/tickets")
    @roles_required("ticket-reader")
    def tickets() -> str:
        sample_tickets = [
            {"id": "HD-2041", "service": "Email", "severity": "Low", "status": "Open"},
            {"id": "HD-2042", "service": "VPN", "severity": "Medium", "status": "Investigating"},
            {"id": "HD-2043", "service": "Laptop", "severity": "Low", "status": "Resolved"},
        ]
        return render_template("tickets.html", tickets=sample_tickets)

    @app.get("/iam-admin")
    @roles_required("iam-admin")
    def iam_admin() -> str:
        return render_template("iam_admin.html")

    @app.get("/audit")
    @roles_required("auditor", "iam-admin")
    def audit() -> str:
        entries = list(reversed(audit_log.entries()[-40:]))
        verification = audit_log.verify_chain()
        return render_template("audit.html", entries=entries, verification=verification)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "accessops-portal",
            "issuer": app.config["OIDC_ISSUER"],
            "audit_chain": audit_log.verify_chain(),
        }

    @app.errorhandler(403)
    def forbidden(_: Any) -> tuple[str, int]:
        return render_template("forbidden.html"), 403

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=False)
