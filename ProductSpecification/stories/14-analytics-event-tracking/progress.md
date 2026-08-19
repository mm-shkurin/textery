# Story 14: Analytics Event Tracking — Progress

Shared story-level file: Spec checklist, narrative, and decisions. Backend/Integration/
Security/Load/Infrastructure scenario state lives in `progress-backend.md`; Frontend
scenario state in `progress-frontend.md`. `ProductSpecification/stories.md` is the
cross-file rollup.

## Spec
- [x] interview
- [x] story
- [S] mockups (analytics instruments the screens that already exist — this story adds no
      new UI surface; UI 3.4 and Sec 4.3 explicitly assert the existing controls and
      refusals are kept as they are)
- [x] api-spec
- [x] test-spec

## Governing principle

**Analytics adapts to the existing application. The existing application is not changed
for analytics.** Recorded by the developer on 2026-08-19 and binding on every scenario
below. Consequences already baked into the test spec:

- Emission is fail-open — a recorder that fails, hangs or refuses never changes an
  existing route's answer (API §12, decision `A1 + B2`).
- No new refusal reason on an existing route. Over-bound `utm_*` are dropped as a set;
  `/auth/register` and the OAuth handshake answer exactly as before (API §7.5, §7.5a).
- `session.py` pool settings are read, not set (Infra §3.3). The load scenarios measure
  against the pool the application actually runs with.
- A missing geolocation configuration does not fail the boot (Infra §3.1, §2.x).

If implementation turns up a case where the analytics outcome cannot be reached without
changing existing behaviour, **stop and report** — do not change it on the way past.

## Decisions

**2026-08-19 — Load §3.1 (`LIMIT` on `list_stale`) is out of scope**
`03_Load_Tests.md` §3.1 is marked `[S]`. It requires bounding
`GenerationStorage.list_stale`, which has no limit today; that changes how the existing
recovery sweep behaves for every generation. The risk is real and pre-existing, and Story
14 does not need it fixed — the requeue path emits nothing by design, so a recovered row
costs this story no extra write. Carried as technical debt in
`ProductSpecification/tasks/7-refactoring-bound-stale-generation-sweep/`, with the
scenario's Gherkin and threshold intact. `Load-Ext` §2.1 (sweep fan-out) is unaffected.

**2026-08-19 — `analytics_events.visitor_id` is nullable**
Confirmed. Every generation in flight across the migration has no recorded visitor, and a
sentinel UUID would add one enormous fake browser to every count Story 15 makes. The
browser ingest route still requires a visitor and still refuses without one (API §2.3) —
the nullability exists for the rolling-deploy window on the server-emitted side, not as a
relaxation of the ingest contract. Asserted by `04_Infrastructure_Tests.md` §1.4a.

**2026-08-19 — the five contract decisions the test spec was blocked on**
All five are answered and recorded in `endpoints.md` § "The five decisions the test spec
was blocked on"; `tests/00_Hazard_Scan_Record.md` maps each to the scenario that asserts
it. No open contract question remains.

**2026-08-19 — the acceptance layer may read `analytics_events` directly**
Approved by the developer at the first RED work unit. `acceptance/clients/database/analytics_event_probe.py`
opens its own `asyncpg` connection and reads the row back with raw SQL. This is the
first file of its kind in `acceptance/` and later stored-row scenarios (§2.4, §3.x, §7,
§11) build on it.

The reason it is needed: both `Then`s of API §1.1 are claims about stored state, and
`endpoints.md` ships no read surface on purpose ("reading is Story 15"). The DSL
Technical Reference pins the second one to literally `analytics_events.user_id IS NULL`,
so the assertion is either made against the database or it is not made at all.

Why it does not break the module's contract: the probe imports no backend module, so
there is no compile dependency on backend internals (`pytest.ini`) — it speaks SQL to
the same Postgres from a different process. That also satisfies «a fresh read» more
strongly than a second `AsyncSession` would: `create_session_factory` sets
`expire_on_commit=False`, so a re-read inside the writing session is served from the
identity map and would pass on a row Postgres never received. A separate process has no
identity map to be served from.

Constraint carried forward: the probe selects columns by name, never `*`, and asserts
`DATABASE_URL` rather than defaulting to localhost — a probe that silently fell back
could read a different database from the one under test and report "nothing was stored"
about a row that exists.
