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

- [ ] I1 — `state` is server-minted, validated on callback, single-use; forged/replayed/missing state is refused, never a session
- [ ] I2 — handoff code redeem is atomic: two concurrent exchanges yield exactly one 200
- [ ] I3 — a handoff code past its TTL does not exchange
- [ ] I4 — no JWT in any URL or redirect header; tokens only in the exchange response body
- [ ] I5 — no handoff code, token or provider secret in the logs
- [ ] I6 — identity unique per (provider, subject); email NFC-normalized + case-folded
- [ ] I7 — missing provider config fails fast at boot, never a quiet half-configured start
- [ ] I8 — an OAuth email matching an existing password account is NOT silently linked

## Foundation

- [ ] `OAuthProvider` port in usecase + `FakeOAuthProvider` test double (mirrors `GenerationProvider`/`FakeProvider`); tests never reach the real Yandex
- [ ] Domain: OAuth identity, CSRF state, one-time handoff code
- [ ] DB: identities + handoff-code tables, alembic migration on the current head
- [ ] Composition root: Yandex adapter wired, config fail-fast at boot (I7)

## Backend Scenarios (`tests/01_API_Tests.md`)

- [ ] 1.1 Start redirects to the provider
- [ ] 1.2 Unknown provider is rejected
- [ ] 2.1 A valid handoff code returns a session (Story 7 login body)
- [ ] 2.2 A replayed code is rejected
- [ ] 2.3 An expired code is rejected at the TTL boundary
- [ ] 2.4 An over-length code is rejected before lookup
- [ ] 2.5 Concurrent exchanges of one code yield exactly one session
- [ ] 2.7 An empty or missing code is rejected server-side
- [ ] 3.1 First sign-in auto-creates one verified account
- [ ] 3.8 OAuth email colliding with an existing password account does not overwrite it

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

- [ ] 1.1 A crafted callback redirect target cannot drive an external redirect
- [ ] 2.1 The callback error value is never rendered raw
- [ ] 5.1 Repeated OAuth requests are rate-limited
- [ ] 6.1 Privileged fields in the exchange body are ignored
- [ ] 7.1 Failure responses carry no internal detail

## Integration / Load / Infrastructure Scenarios

Not started — after the demo.
