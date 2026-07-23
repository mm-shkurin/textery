# Story 16 — carryover (reduced-TDD debt, backend layer)

Written as the work happens, not at the end. Each entry: what was cut, why, and what
restores it. The executable form of this list is
`ProductSpecification/tasks/6-refactoring-oauth-tdd-backfill/progress.md`.

## 2026-07-22 — VK has no credentials

`infra/.env` has `YANDEX_CLIENT_ID` / `YANDEX_CLIENT_SECRET` and nothing for VK. Yandex is
carried end to end; `vk` stays in the contract enum and answers a named configuration error.
Not stubbed, not aliased to Yandex — a stub that looks configured is the exact failure the
tripwire list forbids. Restore: real VK ID credentials, then run the Yandex scenario list
against `vk`.

## 2026-07-22 — redirect URI is not in `infra/.env`

`endpoints.md` says `client_id` / secret / redirect_uri / scopes all come from `infra/.env`
and fail fast at boot. Only the id and secret are there. The redirect URI must match what is
registered in the Yandex OAuth app, so it cannot be invented here — it is read from
`YANDEX_REDIRECT_URI` and boot fails when unset (I7). Needs the real registered value before
the demo can run against live Yandex; the Fake provider path does not need it.

## 2026-07-23 — BLOCKER RESOLVED: OAuth config belongs in `backend/.env`, not `infra/.env`

The earlier "compose does not pass OAuth env" entry below misdiagnosed *where* the
config goes. The `backend` service already loads `env_file: ../backend/.env`, and
`backend/.env` is inside this session's boundary (and gitignored). So OAuth config was
added there — `OAUTH_PROVIDER=fake`, `OAUTH_HANDOFF_CODE_TTL_SECONDS=5`,
`OAUTH_FRONTEND_CALLBACK_URL`, `YANDEX_REDIRECT_URI`, and `YANDEX_CLIENT_ID`/
`YANDEX_CLIENT_SECRET` (mirrored from `infra/.env` so the I7 fail-fast passes). No edit
to `infra/` was needed; the compose `environment:` block is untouched. The real-Yandex
demo still needs the registered `YANDEX_REDIRECT_URI` value (placeholder for now).

Test-runner env: the pytest process (host) also needs `YANDEX_CLIENT_SECRET` (I5
`provider_secret` fixture) and `OAUTH_HANDOFF_CODE_TTL_SECONDS` (I3 `expired_code`
fixture) in `os.environ`. `infra/.env` carries the secret; export
`OAUTH_HANDOFF_CODE_TTL_SECONDS=5` inline when running the acceptance gate so it matches
the container's TTL.

## 2026-07-23 — compose does not pass OAuth env into the backend container (superseded — see entry above)

`infra/docker-compose.yml` `backend` service takes `env_file: backend/.env` and an
`environment:` block that never lists `YANDEX_CLIENT_ID` / `YANDEX_CLIENT_SECRET`. Vars in
`infra/.env` are only interpolated by compose itself (`${...}`) — they do not enter the
container process. So the Yandex credentials that exist in `infra/.env` never reach the app,
and every OAuth acceptance test fails before it starts. Fix: add `YANDEX_CLIENT_ID`,
`YANDEX_CLIENT_SECRET`, `YANDEX_REDIRECT_URI`, `OAUTH_HANDOFF_CODE_TTL_SECONDS`, and
`OAUTH_PROVIDER=fake` (for the test run) to the service `environment:`. `infra/` is outside
this session's file boundary — not touched, awaiting the go-ahead.

## 2026-07-23 — domain + port shipped without their unit tests

`oauth_identity.py`, `oauth_state.py`, `handoff_code.py`, and the `OAuthProvider` port landed
this session under reduced-TDD with no usecase/domain unit tests yet — the invariant gate is
the only thing exercising them, and only end-to-end. Backfill: unit tests for state TTL/
single-provider binding, handoff-code TTL boundary (`>=`), and identity `(provider, subject)`
invariants. Tracked as task 6 Step 1.

## 2026-07-22 — reduced-TDD ceremony cut across the whole story

Per-step red/green commits collapsed to one commit per scenario. Skipped sub-skills:
`/test-review`, `/test-coverage`, `/refactor`, `/agent-review`, `/premortem`, and the formal
`adapters-discovery` gate. Statements-DSL polish kept minimal. Restore: task 6, one step per
scenario.

## 2026-07-23 — frontend contract confirmed + callback `provider` param added

Frontend session verified the 3-endpoint contract. One real gap found and fixed: the
callback redirect carried only `?code=`/`?error=`, never `provider=`, though the frontend
callback page keys its copy off the slug. Added `&provider=<slug>` to both legs (commit
`5c8bff8`); slug is always the exact lowercase registry match. Two coordination notes
recorded in progress-backend.md: `?error=` is a single generic `oauth_failed` (no
user-cancel distinction — deliberate), and the app-wide 5xx handler is codeful
(`INTERNAL_ERROR`), so the frontend retry classifier must treat any 5xx as retryable.

## 2026-07-23 — rate-limiting DONE (Security 5.1 / hazard G6)

Implemented per-source, per-leg fixed-window limiting on all three OAuth routes. Design
notes for future sessions:
- **Store: Postgres, not Redis.** Redis is up but has zero Python wiring; Postgres is
  fully wired (UoW, migrations, delete-RETURNING pattern). New table `oauth_rate_limits`
  (`bucket_key`, `window_start` bigint, `request_count`), migration `1a2b3c4d5e6f`
  (down_revision `0f1a2b3c4d5e`). One atomic `INSERT ... ON CONFLICT DO UPDATE
  ... RETURNING count` per hit → multi-instance safe.
- **Clean split:** `RateLimiter` port + `AllowAllRateLimiter` default + `OAuthRateGuard`
  helper in `usecase/src/auth/oauth/rate_limiter.py` (guard is a shared helper, NOT a
  usecase — the three legs each call `check(leg, source, now)` first). Adapter
  `SqlAlchemyRateLimiter` commits its own increment on the request session, so the hit
  counts even when the guarded op rolls back (throttled/failed leg). Rate check is always
  the FIRST op, so its early commit flushes nothing else.
- **429 via existing machinery:** new code `OAUTH_RATE_LIMITED` → added to the
  `_ERROR_CODE_STATUS_MAP` (429), alongside `RESEND_COOLDOWN_ACTIVE`. No app-wide handler
  change. Callback throttle returns a 429 JSON, not a redirect (the guard raises
  `ValidationException`, which the router's `OAuthCallbackError`-only except does not catch).
- **Source = rightmost X-Forwarded-For** (nginx appends the real client; earlier hops are
  spoofable) else socket peer. Best-effort abuse bound — NO invariant rests on it.
- **Test isolation quirk:** the 5.1 acceptance tests flood a UNIQUE spoofed XFF per test,
  so each flood is its own bucket and the shared localhost bucket the rest of the suite
  runs on is never spent. Limit 40 keeps localhost well clear. `configured_rate_limit()`
  in `oauth_scope.py` reads `OAUTH_RATE_LIMIT_MAX_REQUESTS` (export it for the test host).
- **Config in `backend/.env`:** `OAUTH_RATE_LIMIT_MAX_REQUESTS=40`,
  `OAUTH_RATE_LIMIT_WINDOW_SECONDS=60`. Not `infra/.env`.
---

# Story 16 — Carryover (frontend layer)

Enduring quirks and decisions promoted from completed scenarios. Read on resume.

## Quirk: jsdom applies no CSS — shell reuse needs a class-contract test
**Quirk:** a callback/auth screen whose shell lives in an imported stylesheet plus classnames has nothing in the jsdom suite that can go RED if the CSS import or an `auth-card`/`auth-subtitle` classname is dropped — the OAuth error state shipped with no shared classes and no test caught it.
**Where:** frontend/src/features/auth/components/ (shared `.auth-card`/`.auth-subtitle` from AuthForm.css).
**Implication:** every screen reusing the shared shell needs an explicit test asserting the exact `class` attribute; real CSS correctness stays uncovered until the backend-gated selenium pass.
**From:** scenario 3.1 (valid-handoff-code-signs-in)

## Decision: authenticated callback rejection is broad, not error-code-scoped
**Decision:** On an exchange rejection the callback redirects to the app shell whenever `isAuthenticated()` is true — any late/duplicate failure, not only an already-used code.
**Why:** Spec is deliberately broad; sessionStorage is tab-scoped so an authenticated callback means signed-in this session, and token expiry is the refresh layer's concern.
**Where applied:** OAuthCallback `.catch`, frontend/src/features/auth/components/OAuthCallback.tsx.
**From:** scenario 3.3 (late-duplicate-rejection-ignored)

## Quirk: a bare Error is a transport/network failure to isLoginNetworkError
**Quirk:** `isLoginNetworkError` returns true for any rejection lacking an `errorCode` prop, so a bare `Error` is treated as a network failure and (unauthenticated) routes the callback to `/login`, not the terminal error card.
**Where:** frontend/src/features/auth/utils/loginErrorHandling.ts, consumed by OAuthCallback `.catch`.
**Implication:** A callback test wanting the terminal `oauth-callback-error` path must reject with a business-shaped `{errorCode:…}` value, never a bare `Error`.
**From:** scenario 4.2 (network-failure-retry-affording)

## Quirk: only a codeless 5xx is retry-classified; a coded 5xx is terminal
**Quirk:** `toAuthApiError` attaches `status` only on the codeless path, and `isLoginNetworkError` keys network-ness off `status>=500`; a 5xx carrying an `error_code` has no status → classified NOT-network → terminal error, not retry.
**Where:** frontend/src/features/auth/api/apiError.ts + loginErrorHandling.ts.
**Implication:** Backend must emit 5xx as codeless (FastAPI default is), or the classifier must widen to status>=500 regardless of errorCode — else a server outage dead-ends OAuth users on the terminal screen.
**From:** scenario 4.2 (network-failure-retry-affording)

## Quirk: the coded-5xx-is-terminal rule now has an INTERNAL_ERROR exception (Task 6)
**Quirk:** `isLoginNetworkError`'s final fall-through returns `hasErrorCode(error,'INTERNAL_ERROR')`, so a status-less codeful `{errorCode:'INTERNAL_ERROR'}` (the backend's generic 500) IS retry-classified — partially superseding the carryover entry above. The widening keys on that ONE sentinel; every other coded-but-statusless business error (INVALID_CREDENTIALS, INVALID_OR_EXPIRED_OAUTH_CODE) still returns false → terminal.
**Where:** frontend/src/features/auth/utils/loginErrorHandling.ts.
**Implication:** OAuth 5xx now shows the retry banner, not the terminal card. No end-to-end test drives a real backend 500 body through `toAuthApiError` — if the live backend spells the code differently (INTERNAL_SERVER_ERROR / lowercase), the fix is a silent no-op behind a green suite.
**From:** Task 6 (oauth-5xx-terminal-not-retry)

## Quirk: MemoryRouter rerender + no-op navigate mock can't clear location.state
**Quirk:** A test that mounts under `MemoryRouter` with a mocked no-op `useNavigate` cannot make an effect's `navigate(...,{state:{}})` actually clear `location.state` — MemoryRouter ignores changed `initialEntries` on rerender, so a component reading live `location.state` and one reading a captured local copy are indistinguishable in that setup.
**Where:** frontend/src/features/auth/components/__tests__/ (OAuthErrorBanner.staleBanner vs survivesScrub).
**Implication:** To prove a component survives its own history-state scrub (capture-locally vs blank-on-scrub), the discriminating test must leave react-router REAL so the scrub genuinely mutates state; a no-op-navigate + rerender guard is non-discriminating.
**From:** scenario 4.1 (provider-error-distinct-message)
