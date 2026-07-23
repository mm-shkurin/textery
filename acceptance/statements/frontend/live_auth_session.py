"""Mints a REAL backend-issued session for auth-gated frontend flows.

A seeded sessionStorage token is enough for purely client-side screens (the type and mode
modals render identically whether the token is real or fake). It is NOT enough for any screen
that calls the API on mount or submit — the manual editor's `createDocument`, the chat
workspace's generation POST: the backend answers a fake token with 401, the client clears the
session, and the app collapses to the landing.

So those flows need a token the backend actually signed. This drives the same
register -> verify -> login round trip a human would, over HTTP, and hands back the tokens for
the caller to place in sessionStorage.

The verification code comes back in the register response body (the email adapter is mocked in
this environment), which is what makes the round trip scriptable at all.
"""

import os
import uuid

import httpx

# Any password satisfying the registration policy; the account is throwaway.
_PASSWORD = "Str0ng!Pass"
_REQUEST_TIMEOUT_SECONDS = 10


class LiveAuthSession:
    """One freshly registered, verified, logged-in account and its tokens."""

    def __init__(self, email: str, access_token: str, refresh_token: str):
        self.email = email
        self.access_token = access_token
        self.refresh_token = refresh_token


def _backend_base_url() -> str:
    # Mirrors ApplicationClient: the published backend port is per-checkout and lives in
    # infra/.env, so it arrives here as an env var rather than a literal.
    return f"http://localhost:{os.environ.get('BACKEND_PORT', '8000')}"


def issue_live_session() -> LiveAuthSession:
    """Register, verify, and log in a brand-new account; return its real tokens.

    A new account per call keeps tests independent — no shared state, no ordering coupling,
    and no cleanup step that could leave a half-verified account behind for the next run.
    """
    email = f"acceptance-{uuid.uuid4()}@example.com"
    with httpx.Client(base_url=_backend_base_url(), timeout=_REQUEST_TIMEOUT_SECONDS) as client:
        register = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": _PASSWORD, "confirm_password": _PASSWORD},
        )
        assert register.status_code == 201, (
            f"live-auth setup: register expected 201, got {register.status_code}: {register.text}"
        )
        code = register.json().get("verification_code")
        assert code, f"live-auth setup: register returned no verification_code: {register.text}"

        verify = client.post("/api/v1/auth/verify", json={"email": email, "code": code})
        assert verify.status_code == 200, (
            f"live-auth setup: verify expected 200, got {verify.status_code}: {verify.text}"
        )

        login = client.post("/api/v1/auth/login", json={"email": email, "password": _PASSWORD})
        assert login.status_code == 200, (
            f"live-auth setup: login expected 200, got {login.status_code}: {login.text}"
        )
        body = login.json()

    return LiveAuthSession(
        email=email,
        access_token=body["access_token"],
        refresh_token=body["refresh_token"],
    )
