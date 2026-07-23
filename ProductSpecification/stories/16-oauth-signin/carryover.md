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

## 2026-07-23 — biggest open backend gap: rate-limiting not implemented

`endpoints.md` G6 requires start/callback/exchange to be rate-limited (Security 5.1). Not
done. Everything else remaining is edge-scenario coverage or tests; this is the one missing
piece of named production behavior. Restore: add rate-limiting on the three OAuth routes and
the 5.1 acceptance test.
