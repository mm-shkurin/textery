# RECONCILE — Story 7 (Authorization)

Phase A classification. Written 2026-07-20 (reconcile session, read-only vs code).
Legend: **legit** = no framework gap (drop). **deferred** = behavior/leg never built → backlog Phase C. **stale** = skip reason false TODAY, proven against code → backlog Phase B (urgent).

## Acceptance-test skips (`@pytest.mark.skip`)

| file:line | type | reason today | what to do | layer |
|---|---|---|---|---|
| `acceptance/tests/backend/authorization/test_verify_valid_code_acceptance.py:6` | **stale** | Skip claims `/verify` "not wired to usecase, returns 500, override withheld until 3.2". FALSE: `main.py:114` has `app.dependency_overrides[get_verify_account_usecase] = create_verify_account`; rejection branches 3.2–3.6 all live in `backend/usecase/src/auth/verify_account.py:40-49`. | Un-skip, run green against live backend. If it passes → mark 3.1 `[x]` with real e2e. | backend |

## Backend progress `[S]` — trimmed-cycle acceptance legs (`progress-backend.md`)

Skip reason `"no acceptance test (trimmed cycle); /login not wired live (see 5.1)"` recurs for scenarios 5.x/6.x at lines 327, 401, 456, 474, 504.

| lines | type | reason today | what to do | layer |
|---|---|---|---|---|
| progress-backend.md:327,401,456,474,504 | **stale** | `/login` **and** `/refresh` ARE wired live now: `main.py:115` (`get_login_user_usecase`), `main.py:116` (`get_refresh_access_token_usecase`). The "not wired live" justification is dead. Usecase-level tests exist; the missing acceptance-leg (real HTTP through the border) is now buildable. | Add acceptance tests driving live `/login` + `/refresh` (happy + rejection). Then convert these `[S]` to `[x]` with e2e proof. | backend |
| progress-backend.md:144,162,170,194,197,205,210,294 | **deferred** | `red-acceptance` skips justified by genuine "no HTTP-observable lever" (server-generated uuid4 seam, combining-char password w/ no `/login` at that time, generic-400 branches). Verify/reject e2e leg still absent, but not code-false. | Build the missing acceptance legs for verify happy + rejection (3.1–3.6) once un-skip above lands; the rejection branches exist, only e2e coverage is owed. | backend |

## Backend progress `[S]` — genuine no-gap (drop, do NOT backfill)

**legit** — no port / guard pre-exists / trivial pass-through / declarative-DTO-blind-to-coverage:
lines 25,30–33,42,44,102–105,110–113,120,121,137–140,148–151,158,163–167,174,183,192,198,206,209,328,402,457,475,496,505,513,572.
These are the framework working correctly (Email length guard from 1.1 reused, DB unique-constraint from 2.2 reused, `Password` isinstance guard, `String(6)` column, `_NullUnitOfWork` coverage pins already-green, etc.). Verified representative samples against code; no action.

## Frontend progress `[S]` (`progress-frontend.md`)

| lines | type | reason today | what to do | layer |
|---|---|---|---|---|
| 281,305,339 | **legit** | `green-selenium (BLOCKED — no route in App.tsx)` — explicitly **superseded** by the routing sub-cycle; real completion is the later green-selenium entry. No gap. | none | frontend |
| 390,391,394,395 | **deferred** | `red/green-frontend-api (login/confirm)` — "no real login/verify-confirm API call exists yet". Login endpoint now live server-side (main.py:115), but frontend `authApi` login/confirm wiring is a separate build. Not code-false on the frontend side; behavior genuinely deferred. | Build frontend login/confirm API call + red→green when the frontend consumes `/login`. | frontend |
| 278,279,302,303,349,350,361,362,371,372,408,409,418,419,428,429,438,439,653,654,663,664 | **legit** | `red/green-frontend-api` "no API call — page-display / client-side toggle / focus-advance / pure routing". No port. | none | frontend |
| 334–337,353,452–457,560 | **legit** | coverage `[S]` — guard/branch already correct, "no RED achievable" (throwaway test passed born-green). Framework working. | none | frontend |
| 285,309,343,355,365,375,402,412,422,432,442,657,667 | **legit** | `demo` skipped per convention (visual-only, non-gating). | none | frontend |

## Net backlog for Story 7

- **Phase B (stale, urgent):** un-skip `test_verify_valid_code_acceptance.py`; add `/login` + `/refresh` acceptance legs (reason string "not wired live" is dead).
- **Phase C (deferred):** verify/reject acceptance e2e (3.1–3.6); frontend login/confirm API consumption.
- Everything else: **legit** — drop.
