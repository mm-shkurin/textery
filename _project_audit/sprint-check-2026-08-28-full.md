# /sprint-check — full (both layers) — Stage B — 2026-08-28

Stage B only, by the owner's instruction. Stage A was not re-looped; its last
confirmed scores stand from 2026-08-27.

| | |
|---|---|
| Branch | `dev` |
| HEAD at report time | `d7b72abb` |
| Scope | full — Stage B both layers, both repositories |
| Stage A (carried, not re-run) | backend **2.5 / 3.0** · frontend **2.5 / 3.0** |
| Probes | **87 PASS / 8 WAIVED / 0 FAIL**, unchanged before and after the fixes |

## Stage 0 — the gate

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Deployed link exists and the app works | not re-checked this run | Stage B is file-and-history work; carried from 2026-08-27 |
| 2 | Every artifact in GitVerse | PASS | both remotes present and fetchable |
| 3 | Release branch carries the sprint's work | **FAIL (both layers)** | `gitverse-backend/main` = `377dcabd`, `gitverse-frontend/main` = `4d198630`. Neither carries yesterday's second pass, today's three commits, or the IP-bound password routes. |
| 4 | What was demoed is in the code | not assessable here | needs the pitch's claim list |

**Every score below is provisional.** Gate item 3 has now been open across two
consecutive runs. Nothing in this report reaches the jury until both layers are
pushed; that push is outward-facing and has not been made.

## Scores (provisional — gate item 3 open)

| Criterion | back | front | Movement today |
|---|---|---|---|
| Git-репозиторий, README, Wiki | **1 / 1** | **1 / 1** | judgment lane found real defects in both; all fixed this run |
| Консистентность, арх. стиль | **0.5 / 1** | **0.5 / 1** | 1 → 0.5 — the judgment lane found what the probes cannot |
| Качество кода (Code Smells) | **0.5 / 1** | **0.5 / 1** | 1 → 0.5 — same reason |
| Тест-кейсы | **2 / 2** | **2 / 2** | back 1 → 2: story 14 converted |

Technical aspect: **backend 4 / 5**, **frontend 4 / 5** → rounds to **4 / 5**, provisional.

Yesterday's report scored consistency and smells 1/1 on a probe-clean run. That was
too generous: the probes were clean then too, and today's judgment reviewers — fresh
context, told to hunt classes rather than files — found real findings in both layers
of both criteria. The drop is a correction of yesterday's grading, not a regression in
the code.

## Regression watch

No `source:` probe is non-PASS. The eight WAIVED items are unchanged and unexpired
(`GIT-BULK`, `GIT-DIRECT-MAIN`, `GIT-LANGUAGE` per layer, `SMELL-DUPLICATION@back`,
`SMELL-LONG-FUNC@front`), each waiver stating in its own text that it hides the
finding from this report and not from the jury.

## Fixed this run

**Тест-кейсы, backend 1 → 2** (`012052ec`). Story 14 — the only story delivered this
sprint — carried 177 Gherkin scenarios: `### 1.1` and a `Given/When/Then` block, no
identifier, no test data, no status column, expected results as vague as "the event is
recorded". Its own frontend sibling was already in the project template, so the story
shipped in two formats. All ten backend files converted to `TC-14-<suite>-<x.y>` with
the six-field table, original numbering preserved so every cross-reference still
resolves, a shared test-data table per file. Values read out of the code — error codes
and messages from `analytics_error_codes.py`, the status map from
`exception_handlers.py`, the ten `accounts` columns from migration `d6e7f8a9b0c1`, the
bounds from `transport_defaults.toml`. `docs/testing/README.md` drops the paragraph
admitting the old format; 707 base + 192 extended = 899 now agrees with
`grep -c '^### TC-'` over the published copies.

**Git/README, backend** (`f484b977`). The quick start could not be followed: `alembic`
ran before the database existed and before any variable was set; the documented
`PYTHONPATH` omitted `adapters/geolocation_provider/src` and `application/src/app`,
which `container/analytics_wiring.py` needs at module scope, so the documented command
ended in `ModuleNotFoundError` — verified, and verified fixed (the import now reaches
`DATABASE_URL is not set`, the next real step); `cp .env.example .env` was inert,
because nothing in the repository loads a `.env` and the reader was never told to
export. Plus `sync_test_cases.py --check` missing from the list claiming to be exactly
what CI runs, and a `shortlog` figure of 468 against the README's own command answering
476. `dependency_wiring.py` claimed a `sys.path` setup `main.py` records as deleted.

**Git/README, frontend** (`d7b72abb`). The Структура section omitted `features/profile`
(a whole shipped story), `shared/analytics` and `shared/identity` (this sprint's newest
code, first thing in the CHANGELOG) and `shared/hooks`. README claimed every gate
script has a self-test where two do not, contradicting CONTRIBUTING, which states the
true narrower rule. Three drifted counts: `shortlog` 663 → 668, unit tests 960 → 1069
across 240 files, and CONTRIBUTING's "12 Cyrillic against 48 Latin" — a windowless
claim, where the layer's 675 subjects are 94 against 581 and the last sixty are 14
against 46. `frontend/docs/testing/README.md` said «десяти историй» over eleven
directories and omitted story 14's row.

## New findings — not fixed

Ranked by what a grader hits first. None was auto-fixed: each changes runtime
behaviour or architecture.

1. **`features/history` is 1 125 lines of unreachable production code.**
   `DocumentGenerationFlow.tsx:72` routes `step === 'history'` to `ProjectsPage`;
   `HistoryPage` is imported by no production module, only by its own ~850 lines of
   tests, which inflate the suite past the shipped surface. `DocumentGenerationFlow.tsx:63`
   admits it in a comment instead of deleting it. A grader opening `src/features/`
   sees two slices listing the same documents and only one that runs. The largest
   single finding in either repo — and deleting a slice plus its tests is the owner's
   call, not a mechanical fix.
2. **nginx appends no `X-Forwarded-For`.** `infra/docker/nginx/frontend.conf:41-42`
   sets `Host` and `X-Real-IP` only, while `client_context.py` trusts
   `TRUSTED_PROXY_HOPS=1` and counts entries from the right. Deployed behind the host
   proxy it works by accident — the missing hop cancels the trusted-hop count.
   Deployed without one, `client_ip_of` falls through to the nginx container's address,
   which is exactly the failure its module docstring says must not happen: one
   geolocation country for everyone and one rate-limit bucket for everyone. The fix is
   two coupled edits (`proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for` and
   `TRUSTED_PROXY_HOPS=2`) and depends on the real chain — fixing only the nginx side
   makes it worse.
3. **Neither compose file forwards the geolocation or analytics variables** into the
   backend container, so this sprint's story runs on defaults in the deployed stack.
4. **`endpoints.md` contradicts the shipped route.** Its "Residual this contract does
   not own" says a non-JSON body answers FastAPI's `{"detail": …}` 422;
   `analytics_router._parsed` answers the canonical `400 INVALID_PAYLOAD`. The residual
   was closed for this route and the spec never caught up. The test cases assert the
   code; the spec still needs the edit.
5. **`analytics_events_create.yaml` documents `503`** when the rate-limit store is
   unavailable, where `RecordAnalyticsEvent._guard_the_rate` answers `429 RATE_LIMITED`.
   One of the two is wrong and it is a contract question, not a doc typo — 503 says
   "our limiter is down", 429 says "you are limited", and a client acts differently.
6. **`DocumentCreation` is confirmed a half-binding.** Yesterday's suspicion, now with
   line numbers: `create_document.py:26-29,61-63` and
   `create_document_from_generation.py:54-60,156-157` still hold the repository and the
   unit of work as their own fields and use them directly in recovery.
7. **`unit_of_work: UnitOfWork | None = None` falling back to `NullUnitOfWork`** on four
   document usecases. Wiring is correct today, so the guard exists for test
   convenience — but a wiring omission would drop every commit silently.
8. **`generation_rules` was extracted and no call site repointed** — 13 modules still
   reach the constants through a re-export shim held open by `# noqa: F401`. A
   file-size dodge wearing the shape of a boundary.
9. **Seven wire error codes are still bare strings** (`account_name.py`, `avatar.py`,
   `title_update.py`, `deletion_confirmation.py`, `email_validation.py`) while
   `shared/error_codes.py` declares itself the single vocabulary and narrates the
   migration of the analytics and OAuth slices onto it.
10. **HTTP media types in the domain.** `domain/src/auth/avatar_format.py:27` holds
    `image/png` and friends, and `dto/auth/avatar_response.py` imports them back out —
    while the sibling `dto/document/export_media_type.py` states the opposite rule in
    an essay and keeps only `ExportFormat` in domain.
11. **Four ways to make an authenticated call in the frontend** (`shared/api/send.ts`,
    `identity/api/profileApi.ts`, `identity/api/identityRequest.ts`,
    `analytics/analyticsClient.ts`) and three error-mapping conventions
    (`features/auth/api/apiError.ts` returns a non-`Error` object,
    `shared/api/failureText.ts` returns a string, `identity/api/profileErrors.ts`
    throws typed subclasses).
12. **`Step = 'landing' | 'type' | 'form' | 'history'`** — the flow state machine still
    speaks the replaced story's vocabulary.
13. **`@tanstack/react-query` is used by two slices**, one of which is the dead one;
    everything else fetches by hand.
14. **`backToLanding` is dead**, kept alive by its own test, with a reducer action
    existing only to serve it.

## Cleared

- **`LandingSection` is not a half-binding.** The two non-adopters are principled and
  the component's own docstring says so: `LandingComparison.tsx:30` puts the shared
  class on an inner element because the dark band bleeds full-width, and
  `LandingFaq.tsx:48` has no section shell at all.
- **`useGeneration.ts` at 199 lines is genuinely decomposed**, not a long function
  wearing helpers.
- **The old God-object storage remark is fixed.** `SqlAlchemyDocumentStorage` is 180
  lines, six owner-scoped methods, one CAS statement.
- **Memoisation is real**, not decorative: the memo'd components get stable references
  from their parents.

## Delta versus `sprint-check-2026-08-27-full.md`

- Fixed: backend test cases (1 → 2), backend README runnability, both layers' stale
  counts and module maps, the frontend testing index.
- Regressed: nothing in the code. Two criteria scored 1/1 yesterday score 0.5 today
  because yesterday's pass graded them off a clean probe run.
- New: 14 findings above, of which the dead `features/history` slice and the
  `X-Forwarded-For` gap are the two worth acting on first.
- Unchanged: gate item 3, now open two runs running.

## Needs a task

- Delete `features/history` and its tests, or route to it. One slice, ~2 000 lines
  including tests.
- `X-Forwarded-For` and `TRUSTED_PROXY_HOPS` as one coupled change, decided against the
  real proxy chain.
- Forward the geolocation and analytics variables in both compose files.
- Resolve 429-vs-503 in `analytics_events_create.yaml` against the handler.
- One error-code vocabulary: migrate the seven bare strings onto `ErrorCode`.
- One authenticated-call path and one error-mapping convention in the frontend.
- Finish or revert the `DocumentCreation` binding and the `generation_rules` extraction.
- No CORS policy in the backend; `UnlimitedSearchSlots` is a no-op throttle; no
  `v0.3.0` tag — all carried unchanged from 2026-08-27.
