# Story 16: OAuth sign-in (VK ID + Yandex ID) — Backend Progress

Layer: backend (`backend/`, `acceptance/tests/backend/`). Frontend progress lives in
`progress-frontend.md` — never edited from this session.

**Mode: reduced TDD until the Friday demo.** Per-scenario red/green commits are collapsed
into one commit per scenario; `/test-review`, `/test-coverage`, `/refactor`, `/agent-review`,
`/premortem` and the formal `adapters-discovery` gate are skipped. Every reduced step is
marked `[S] reduced-TDD <date>, backfill pending` — never `[x]` — and the cut work is
tracked in `ProductSpecification/tasks/6-refactoring-oauth-tdd-backfill/`.

What is NOT reduced: an acceptance test written first and red for every visible outcome,
a usecase test for the core logic, the Clean Architecture port/adapter split for the
provider, the 200-line file limit, and the security invariant gate below.

## Provider credentials

`infra/.env` carries `YANDEX_CLIENT_ID` / `YANDEX_CLIENT_SECRET` only. **Yandex is the
provider carried end to end.** VK has no credentials, so `vk` stays inside the contract
enum and answers a clean, named error — it is never silently defaulted to Yandex and never
stubbed to look configured. See `carryover.md`.

## Security invariant gate (never reduced, never skipped)

`acceptance/tests/backend/oauth/test_oauth_security_invariants.py` — must be green at the
end of every work unit. If an invariant test is red, the production code is fixed or the
session stops; the invariant test itself is never edited, weakened, skipped or xfailed.

**GATE GREEN 2026-07-23** — `12 passed` against the recreated backend image
(`OAUTH_PROVIDER=fake`, `OAUTH_HANDOFF_CODE_TTL_SECONDS=5`). The gate is NOT reduced-TDD
debt: these are the real invariant tests and they pass end to end.

**LIVE YANDEX CONFIRMED 2026-07-23** — full handshake against real Yandex ID succeeded:
`start → Yandex login → callback → exchange → 200`. Created identity `(yandex, 2027708195)`
and verified account `mmm-shkurin2000@yandex.ru`. Two prerequisites found by doing:
(1) the Yandex app must be granted **login:email** or `default_email` is absent and the
callback refuses; (2) real config lives in `backend/.env` (not `infra/.env`). Observability
added along the way (safe, keys/types only — I5 intact): callback logs the refusal reason,
`YandexOAuthProvider` logs the provider error status/body and missing-field keys.

**UNIT BACKFILL GREEN 2026-07-23** — `54 passed` (domain + usecases + registry + both
provider adapters). See task 6. Storage-adapter atomicity tests still owed (need live PG).

- [x] I1 — `state` server-minted, validated on callback, single-use; forged/replayed/missing state refused, never a session (3 shapes) — GREEN
- [x] I2 — handoff redeem atomic: two concurrent exchanges yield exactly one 200 (asyncio.gather) — GREEN
- [x] I3 — a handoff code past its TTL does not exchange — GREEN, TTL is real config `OAUTH_HANDOFF_CODE_TTL_SECONDS`
- [x] I4 — no JWT in any URL/redirect header; tokens only in the exchange body — GREEN
- [x] I5 — no handoff code, token or provider secret in the logs — GREEN
- [x] I6 — identity unique per (provider, subject); email NFC + case-folded — GREEN
- [x] I7 — missing provider config fails fast at boot naming the var — GREEN
- [x] I8 — an OAuth email matching an existing password account is NOT silently linked — GREEN (refused AND password still logs in)

## Foundation

- [S] `OAuthProvider` port + `ProviderIdentity` + errors — `backend/usecase/src/auth/oauth/oauth_provider.py`. Unit tests reduced. `[S] reduced-TDD 2026-07-23, backfill pending`
- [S] Domain — `oauth_identity.py`, `oauth_state.py`, `handoff_code.py`. Unit tests reduced. `[S] reduced-TDD 2026-07-23, backfill pending`
- [S] Usecase ports + usecases — `oauth/{oauth_state,oauth_identity,handoff_code}_repository.py`, `provider_registry.py`, `oauth_error_codes.py`, `start_oauth.py`, `complete_oauth_callback.py`, `exchange_handoff_code.py`. Unit tests reduced. `[S] reduced-TDD 2026-07-23, backfill pending`
- [S] `FakeOAuthProvider` + `YandexOAuthProvider` — new adapter `backend/adapters/oauth_provider/src/oauth_providers/`; selected by `OAUTH_PROVIDER` in `oauth_wiring.py`. Fake impersonates `yandex`, never reaches real Yandex. Unit tests reduced. `[S] reduced-TDD 2026-07-23, backfill pending`
- [S] DB — models + storages (`model/auth/oauth_*`, `access/auth/oauth_*`) + migration `0f1a2b3c4d5e_oauth_tables.py` (down_revision `f7b8c9d0e1a2`, applied clean). State/handoff use delete-RETURNING for single-use/atomic redeem. Unit tests reduced. `[S] reduced-TDD 2026-07-23, backfill pending`
- [S] REST — `router/auth/oauth_router.py` (3 legs, 302 redirects, generic `?error=`) + `dto/auth/oauth_exchange_request_dto.py`; reuses `LoginResponseDto`. `[S] reduced-TDD 2026-07-23, backfill pending`
- [S] Composition root — `container/oauth_wiring.py` (per-request factories, `ProviderRegistry`, config fail-fast I7), re-exported in `container/__init__.py`, sys.path + `dependency_overrides` in `main.py`, `adapters/oauth_provider/src` added to `pyproject.toml` pythonpath. `[S] reduced-TDD 2026-07-23, backfill pending`
- [x] **BLOCKER RESOLVED** — OAuth config goes in `backend/.env` (loaded by the container via `env_file`, inside this session's boundary), not `infra/.env`. Earlier "compose does not pass env" note was a misdiagnosis. `infra/` untouched. See `carryover.md` 2026-07-23.

## Backend Scenarios (`tests/01_API_Tests.md`)

Implemented and proven by the invariant gate (green) end to end, but each still owes its
own dedicated per-scenario acceptance test — collapsed into this work unit under
reduced-TDD, tracked in task 6.

- [S] 1.1 Start redirects to the provider — proven by I4 (start leg). `reduced-TDD 2026-07-23, backfill pending`
- [S] 1.2 Unknown provider is rejected — `ProviderRegistry` raises `UNKNOWN_OAUTH_PROVIDER`; dedicated acceptance test pending. `reduced-TDD 2026-07-23, backfill pending`
- [S] 2.1 A valid handoff code returns a session (Story 7 login body) — proven by I4/I6. `reduced-TDD 2026-07-23, backfill pending`
- [S] 2.2 A replayed code is rejected — delete-RETURNING redeem burns it; dedicated test pending. `reduced-TDD 2026-07-23, backfill pending`
- [S] 2.3 An expired code is rejected at the TTL boundary — proven by I3. `reduced-TDD 2026-07-23, backfill pending`
- [S] 2.4 An over-length code is rejected before lookup — `MAX_HANDOFF_CODE_LENGTH` guard; verified in-process. `reduced-TDD 2026-07-23, backfill pending`
- [S] 2.5 Concurrent exchanges of one code yield exactly one session — proven by I2. `reduced-TDD 2026-07-23, backfill pending`
- [S] 2.7 An empty or missing code is rejected server-side — guard + 422 on missing field; verified in-process. `reduced-TDD 2026-07-23, backfill pending`
- [S] 3.1 First sign-in auto-creates one verified account — proven by I6 (account created, JWT `sub` stable). `reduced-TDD 2026-07-23, backfill pending`
- [S] 3.8 OAuth email colliding with an existing password account does not overwrite it — proven by I8. `reduced-TDD 2026-07-23, backfill pending`

### Deferred to the weekend (named, not forgotten)

- [ ] 2.6 A code minted on one instance is redeemable on another
- [ ] 3.2 Concurrent first sign-ins for one identity create one account
- [ ] 3.3 Email case / normalization / locale variance resolves to one account
- [ ] 3.4 A code that yields no session is not burned
- [ ] 3.5 Extra request fields cannot over-bind on auto-create
- [ ] 3.6 Sign-in failure copy does not reveal account existence
- [ ] 3.7 A large provider subject id is not truncated
- [ ] 3.9 A failed session issue leaves no orphan account
- [ ] 3.10 Recovery after a lost exchange response

## Security Scenarios (`tests/05_Security_Tests.md`)

Covered by the invariant gate above: 3.1 (I2), 3.2 (I4/I5), 4.1 (I1).

## Acceptance harness added this session (oauth-only)

New files, no cross-story impact: `acceptance/statements/oauth_scope.py`,
`oauth_statements.py`, `oauth_runtime_probe.py`,
`acceptance/clients/application/dto/auth/oauth_dtos.py`,
`acceptance/tests/backend/oauth/test_oauth_security_invariants.py`. Point edits to shared
harness: three OAuth methods on `ApplicationClient`, `oauth_statements`/`expired_code`/
`provider_secret` fixtures + imports in `acceptance/conftest.py`. Flagged for review — if the
shared `conftest.py` is off-limits, move the fixtures into a `tests/backend/oauth/conftest.py`.

- [ ] 1.1 A crafted callback redirect target cannot drive an external redirect
- [ ] 2.1 The callback error value is never rendered raw
- [ ] 5.1 Repeated OAuth requests are rate-limited
- [ ] 6.1 Privileged fields in the exchange body are ignored
- [ ] 7.1 Failure responses carry no internal detail

## Integration / Load / Infrastructure Scenarios

Not started — after the demo.
