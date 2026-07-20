# RECONCILE — Story 1 (Auto-generate: доклад)

Phase A classification. Written 2026-07-20 (reconcile session, read-only vs code).
Legend: **legit** / **deferred** / **stale** (see RECONCILE_07.md header).

## Acceptance-test skips

No `@pytest.mark.skip` in `acceptance/tests/**/generation` for Story 1. The landing
hero-subheading issue (plan known-debt #12, `test_landing_page_acceptance.py`) is an
**assert-level** mismatch, not a pytest skip — see below, flagged **needs-verify**.

| item | type | reason today | what to do | layer |
|---|---|---|---|---|
| landing hero-subheading (plan known-debt #12) | **legit (resolved)** | Verified: `test_landing_page_acceptance.py` asserts only `hero-heading` (testid `hero-heading`, matches `LandingPage.tsx:53`) + CTA. **No subheading assert anywhere** in test or `landing_page_statements.py`. The stale-testid debt is already gone. | none — known-debt #12 can be closed. | frontend |

## Backend progress `[S]` (`progress-backend.md`)

| lines | type | reason today | what to do | layer |
|---|---|---|---|---|
| 77,78 | **legit** | `red/green-adapter queue` — `NoOpGenerationQueue` deliberate no-op (known-debt #10/#11); no real arq producer exists to test, generation runs inline via FastAPI `BackgroundTasks`. No port to inject. | none (real queue is a future story, not a backfill gap) | backend |
| 109,117,125 | **legit** | `design` — trivial pass-through (`GetGeneration.execute` pre-existed). | none | backend |
| 124 | **deferred** | `red-acceptance` — "backfilled at usecase+rest layer only 2026-07-10; no top-level `acceptance/` black-box test yet". Genuine missing e2e leg. | Add top-level acceptance test for GET generation once prioritized. | backend |

## `progress.md` (shared) `[S]`

| line | type | reason today | what to do | layer |
|---|---|---|---|---|
| progress.md:23 (P0-6, Integration 1.1) | **deferred** | "successful provider call produces a completed document — verified **manually** end-to-end against real GigaChat, no automated integration test." Real behavior exists; the integration-test leg is absent. | Build the integration test (or explicitly accept as manual-only with rationale). Story 1 Intg column is `—` in stories.md. | backend/integration |

## Frontend progress `[S]` (`progress-frontend.md`)

| lines | type | reason today | what to do | layer |
|---|---|---|---|---|
| 27,28,33,34,37,38,43,44,47,48,53,54,57,58,63,64,67,68,73,74 | **deferred** | `red-selenium`/`red-frontend`/`green-selenium`/`demo` — **framework-skip decision 2026-07-09 (speed measure)**. Code built by hand, "verified by eye in browser" (line 29,39,49,59,69). This is off-framework known-debt #10-class: `[x]`/`[S]` describe behavior no test guards via red→green. | Characterization red first (like Task 3), then real selenium legs against live app; reconcile `[x]` after. Backlog Phase C. | frontend |
| 32,42,52,62,72,96 | **deferred (minor)** | `align-design` — "matched to mockup by eye, no formal align-design pass". | Run `/align-design` formally per scenario, or accept with note. | frontend |
| 20,21,30,31,40,41,50,51,60,61,70,71,91,93,94,95 | **legit** | `red/green-frontend-api` — purely presentational hero/CTA or local UI state, no backend call (`POST/GET /generations` belong to later scenarios). No port. | none | frontend |
| 77 | **legit** | `red-selenium` existence-check remapped per known-debt #8. | none | frontend |
| 98 | **legit** | `demo` — ceremony trim (2026-07-09), visual-only non-gating. | none | frontend |

## Net backlog for Story 1

- **Phase B (stale):** none. Landing hero-subheading (known-debt #12) verified **already resolved** — close it.
- **Phase C (deferred):** off-framework frontend slice (scenarios 1.2/2.1/2.2/3.1/3.2 selenium+frontend, 2026-07-09 speed-skip) → characterization red then e2e; GET-generation top-level acceptance leg (backend); Integration 1.1 automated test (P0-6).
- Queue no-op, trivial-pass-through design, presentational frontend-api: **legit** — drop.
