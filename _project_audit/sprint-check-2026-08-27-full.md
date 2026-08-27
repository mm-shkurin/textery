# /sprint-check — full (both layers) — 2026-08-27

| | |
|---|---|
| Branch | `dev` |
| HEAD at report time | `590bc339` (probes run at `5d8c3ce3` + the env-template fix verified separately) |
| Scope | full — Stage A both layers, Stage B all four criteria, both repositories |
| Stage A final | backend **2.5 / 3.0** (iteration 17, confirmed) · frontend **2.5 / 3.0** (iteration 8, confirmed) |
| Probes | 84 PASS / 11 FAIL, of which 4 regression (was 81/14 with 6 regression at the start of this run) |

## Stage 0 — the gate

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Deployed link exists and the app works | PASS | `README.md:7` names `https://mmshkurin.ru` — `GET /` answers `200` and serves the built SPA; `GET /health` answers `200`. (`/api/health`, `/api/docs` and `/api/v1/openapi.json` are `404` — the health route is served at `/health`, not under `/api`.) |
| 2 | Every artifact in GitVerse | PASS | `gitverse-backend` → `slide_backend.git`, `gitverse-frontend` → `slide_frontend.git`, both refs present and fetchable. |
| 3 | Release branch carries the sprint's work | **FAIL (frontend)** | `gitverse-backend/main` is at `fix(infra): the deploy image never learned about the geolocation adapter`, identical to `dev`'s backend tree — synced. `gitverse-frontend/main` stops at `docs(sprint-check): the gate passes…`; **seven frontend commits exist only on `dev`.** |
| 4 | What was demoed is in the code | not assessable here | Needs the pitch's own claim list. |

The seven unpublished frontend commits are the whole of this sprint's visible work:

```
a40bb546 fix(ui): the manager's walkthrough — dead controls, dark theme, mobile overlap
cfc516b0 perf(generation): the markdown renderer leaves the entry chunk, 360 fit
4c49ec6b feat(generation): the topic form, the wait and the editor are their frames
bf7e3edc feat(generation): the creation modal matches its frame at both breakpoints
d03a9652 feat(projects): «Мои проекты» is the Figma frames, both themes, 360
71ea1f84 feat(landing): the page is the redrawn frame
0acb62a0 feat(landing): «/» opens projects for a session and the pitch for a visitor
```

Every commit this run added — six more — is also unpublished, on both layers.

**Consequence: every score below is provisional.** Code is graded from the release
ref, and the frontend release ref does not carry this sprint. Publishing is
outward-facing and was not done: it needs an explicit decision after reading
`git diff gitverse-frontend/main..dev --stat -- frontend/`. The frontend's
test-case artifacts are the exception — all 23 files under `docs/testing/` on
`gitverse-frontend/main` are byte-identical to `HEAD:frontend/docs/testing`, so
criterion 4 is not affected by the lag.

## Scores (provisional — gate item 3 open)

| Criterion | back | front | Why |
|---|---|---|---|
| Git-репозиторий, README, Wiki | **0 / 1** | **0 / 1** | `GIT-BULK` and `GIT-DIRECT-MAIN` are `regression: True` and FAIL in both layers. By `grading-rules.md` — "any regression item not PASS → 0" — this is 0, not the 0.5 the 2026-08-21 report gave on the same evidence. See *Scoring note*. |
| Консистентность, арх. стиль | **1 / 1** | **1 / 1** | Every `arch`/`style` probe PASS. The judgment lane's two frontend findings (dead memoisation, misplaced module) were fixed in this run; the backend's two (`server_event_recorder` peer call, `document_dtos.py`) are named below and did not change the score. |
| Качество кода (Code Smells) | **0.5 / 1** | **0.5 / 1** | Every regression probe PASS. `SMELL-LONG-FUNC` and `SMELL-DUPLICATION` FAIL as new findings in both layers → 0.5 by the rule. The judgment lane independently scored this 1/1 for both layers, finding no genuine smell; that disagreement is appeal material. |
| Тест-кейсы | **1 / 2** | **2 / 2** | Backend: story 14's 177 cases — the only story delivered this sprint — carry no identifier, description, test data or status. Frontend: all ~289 cases carry the full eight-field template with real values. |

Technical aspect: **backend 2.5 / 5**, **frontend 3.5 / 5**, both provisional.
By the season's rounding rule (prefer rounding up when the two values differ by ≤ 2)
the pair 2.5 and 3.5 rounds to **3 / 5**. Both repo scores are stated above; the
rounded number is not meaningful without them, and none of it may be claimed while
gate item 3 is open.

### Scoring note — a deliberate disagreement with the previous report

`sprint-check-2026-08-21-back.md` scored git-docs **0.5** while `GIT-BULK` and
`GIT-DIRECT-MAIN` were failing regression items, on the reasoning that both are
history and cannot be repaired. `grading-rules.md` says any regression item not
PASS scores 0. This report applies the rule as written. The earlier score was the
kinder reading of the same facts, and a self-audit that rounds itself up is worth
less than one that does not — but the disagreement is recorded rather than
silently resolved, because if the rule is wrong it is the rule that should change.

## Stage A — audit loop

Both layers ran a fix pass and a confirmation pass with fresh zero-bias auditors.

| Layer | Iteration | Score | Note |
|---|---|---|---|
| back | 16 | 2.5 / 3.0 | before any fix this run |
| back | 17 | 2.5 / 3.0 | confirmation, held |
| front | 7 | 2.5 / 3.0 | before any fix this run |
| front | 8 | 2.5 / 3.0 | confirmation, held |

The frontend confirmation run independently reports the 200-line cap as "genuinely
held … the largest file in `src/` and `scripts/` is exactly 200 lines", which is the
fix from iteration 7 read back by an auditor that never saw it made.

## Regression watch — the grader's own 2026-08-07 remarks

| ID | layer | status | evidence |
|---|---|---|---|
| `DOC-ENV-CLEAN` | front | **PASS** | Regressed mid-run by this run's own README fix — a worked `http://localhost:8001` went into `.env.example` — then fixed at `590bc339`. Recorded because a self-audit that introduces the remark it is checking for should say so. |
| `ARCH-DESIGN-TOKENS` | front | **PASS** | was FAIL: 4 literals in the new landing CSS |
| `DOC-CHANGELOG-FRESH` | front | **PASS** | was FAIL at 27 commits against a 25 limit |
| `TEST-SKIPS` | back | **PASS** | was FAIL: the run-time `pytest.skip` is collection-time filtering now |
| `SMELL-MAGIC`, `SMELL-TYPE-ESCAPE` | back | **PASS** | fixed earlier this sprint, still holding |
| `SMELL-URL`, `SMELL-FS-PATH`, `SMELL-POLICY-IN-CODE`, `SMELL-ENDPOINT-LITERAL` | both | **PASS** | holding |
| `ARCH-PATH-HACK` | back | **PASS** | holding |
| `GIT-BULK` | back | FAIL | `3afbaddd` 45 files, `eb35cafa` 48 files |
| `GIT-BULK` | front | FAIL | `71ea1f84` **71 files** (40 new binaries, a deleted feature, 15 edited components), `bb6633d5` 45, `ce767ac2` 41 |
| `GIT-DIRECT-MAIN` | both | FAIL | history; the policy is documented at `backend/README.md` and `frontend/README.md` |

## New findings

Non-regression FAILs, ranked by what a grader reading the repo cold hits first.

1. `ARCH-SIZE-STYLE@front` — **fixed this run.** Three stylesheets over the
   project's own 200-line hard cap, caught by no gate.
2. `GIT-LANGUAGE` (both) — mixed Cyrillic and Latin commit subjects, 14/46 back and
   15/45 front. History; not repairable.
3. `SMELL-LONG-FUNC` (both) — 10 backend functions and 12 frontend blocks over 30
   lines. The judgment agent read them and calls them threshold artifacts:
   docstring-heavy rather than logic-heavy, and a `useCallback` with a dependency
   array adds three lines to whatever it wraps.
4. `SMELL-DUPLICATION` (both) — 12 six-line pairs each. Largely a probe artifact:
   the rule normalises string literals, so two `.map` rows over a card hash
   identically.

### Fixed this run, beyond the probes

- **`adapters/geolocation_provider/` had no tests at all** while `pyproject.toml`
  counted it in `[tool.coverage.run] source`. 32 tests over `httpx.MockTransport`
  (`4091e9d3`).
- **Three parallel error-code vocabularies** folded into one enum (`a1922c06`).
  mypy found the seam the moment the map's keys became uniform.
- **`memo(ProjectCard)` was dead** — defeated by an object literal rebuilt every
  render; `ProjectsTableRow` had no `memo` at all (`51f18a66`).
- **The frontend quick start could not be run** in the published repo: the one
  required variable was sourced from `../infra/.env`, which exists only in the
  monorepo (`51f18a66`).
- **Three documents contradicted each other or the repository** — README vs
  CONTRIBUTING on branch flow, a citation of a file absent from the split repo,
  «команда из двух человек» against a 663:7 split, «десять историй» against eleven
  (`51f18a66`); and the backend README's «579 кейсов по десяти историям» against
  the 899/eleven in the document it links on the same line (`5d8c3ce3`).
- **A flaky test** — `ManualEditor.dirty.test.tsx` asserted a call count over a
  window whose length machine load decides (`51f18a66`).

## Delta — versus `sprint-check-2026-08-21-back.md` / `-front.md`

No same-scope predecessor exists (`2026-08-20-full.md` is the last full run), so
this compares against the two single-layer reports of 2026-08-21 taken together.

- Probe failures: 14 → **11** across the run, 6 regression → **4**.
- Fixed: `TEST-SKIPS@back`, `ARCH-DESIGN-TOKENS@front`, `DOC-CHANGELOG-FRESH@front`,
  `ARCH-SIZE-STYLE@front`.
- Regressed then repaired inside this run: `DOC-ENV-CLEAN@front`.
- Regressed and standing: none.
- New since 2026-08-21: `ARCH-SIZE-STYLE@front` (introduced by the Figma work,
  fixed here).
- Unchanged: `GIT-BULK`, `GIT-DIRECT-MAIN`, `GIT-LANGUAGE`, `SMELL-LONG-FUNC`,
  `SMELL-DUPLICATION` in both layers.
- Criterion movement: backend testing held at 1/2 (story 14 unchanged); frontend
  testing assessed at 2/2 for the first time under the full eight-field reading;
  git-docs moved 0.5 → 0 in both layers on the scoring-rule correction above, not
  on any new defect.

## Needs a task

Each of these changes runtime behaviour or architecture, so none was auto-fixed.

- **No CORS policy anywhere in the backend.** `grep` for
  `CORSMiddleware|allow_origins|allow_credentials` across `application/src` and
  `adapters/rest/src` is empty. This works only because nginx fronts `/api/`; the
  published standalone repo ships its own `docker-compose.yml` that publishes the
  backend port directly, so a browser client against it fails opaquely. Scope: an
  env-driven origin allowlist plus a test asserting it.
- **`UnlimitedSearchSlots` is a no-op throttle on a public route.** `ListProjects`
  requires a `SearchSlots` port whose wired implementation returns `True`
  unconditionally with a no-op `release()`, so an unindexed content scan on the
  project feed has no concurrency bound at all. Scope: a real slot implementation,
  or removing the port and saying so.
- **No IP-level rate limit on `POST /login`, `/register`, `/resend`.** Only the
  per-account failed-attempt lockout exists, so credential stuffing spread across
  many accounts from one source is unthrottled at the application layer. The
  DB-backed limiter already exists for the OAuth legs and could be reused. Scope:
  wire it to the three password routes.
- **Backend `server_event_recorder.py:83` calls another third-layer adapter** —
  `await SqlAlchemyAnalyticsEventRepository(session).save_new(…)` — which
  `.claude/rules/coding-rules.md` forbids in its own words. One line, but it is the
  repo's own written rule broken inside the repo.
- **`adapters/rest/src/dto/document/document_dtos.py` holds five DTOs** where the
  20 files around it hold one each.
- **Backend story-14 test cases are still Gherkin.** 177 cases across 10 files with
  no identifier, description, test data or status column — the one story delivered
  this sprint, in the format the other ten were migrated off. This is the single
  largest score lever available: it is worth the second point of a double-weighted
  criterion, and it is pure document work. Scope: rewrite
  `ProductSpecification/stories/14-analytics-event-tracking/tests/*.md` into the
  executable template, then `python scripts/sync_test_cases.py`.
- **Frontend has no cases for the redrawn landing.** `71ea1f84` shipped
  `LandingFaq`, `LandingComparison`, `LandingProcess`, `LandingAdvantages`,
  `LandingExport`, `LandingStats`, `LandingTrustedBy`; a grep for their subject
  matter across all 23 case files returns zero hits, and no case anywhere asserts
  either half of this sprint's stated acceptance criteria — "in both themes and at
  360". The only viewport cases are 375×812 and 390×844.
- **`frontend/docs/testing/01-auto-generate-doklad/02_UI_Tests.md:16-18`** still
  tells a tester the generation screens "aren't in the Figma batch yet" and to
  validate against superseded HTML mockups — contradicted by this sprint's own
  commits. A jury opening the story-01 file first reads a factually wrong
  instruction.
- **`package.json` is at `0.3.0` with no `v0.3.0` tag**, so `CHANGELOG.md` cannot be
  tied to a commit range.
- **27 frontend gate scripts, 2,936 lines** — the 2026-08-07 remark named "15+
  hand-written lint scripts" and the number has grown.
  `check-per-file-coverage.mjs` duplicates Vitest's native `perFile` thresholds and
  `check-boundaries.mjs` duplicates a standard import-boundaries lint rule.
