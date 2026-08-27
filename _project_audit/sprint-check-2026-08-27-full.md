# /sprint-check — full (both layers) — 2026-08-27

Second pass. The morning run produced a report; this one applied its findings, then
re-graded Stage B from scratch with fresh reviewers. Test cases are excluded by the
owner's instruction — that criterion belongs to another person and stands at 2/2.

| | |
|---|---|
| Branch | `dev` |
| HEAD at report time | `7d7d1dd5` |
| Scope | full — Stage A both layers, Stage B re-graded, both repositories |
| Stage A final | backend **2.5 / 3.0** · frontend **2.5 / 3.0**, each confirmed |
| Probes | **87 PASS / 8 WAIVED / 0 FAIL** (was 81 PASS / 14 FAIL at the start of the day) |

## Stage 0 — the gate

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Deployed link exists and the app works | PASS | `https://mmshkurin.ru/` → 200; `/health` → 200 |
| 2 | Every artifact in GitVerse | PASS | both remotes present and fetchable |
| 3 | Release branch carries the sprint's work | **FAIL (frontend)** | `gitverse-frontend/main` still stops at `docs(sprint-check): the gate passes…`; the seven Figma commits plus everything from both of today's passes exist only on `dev`. Backend was synced this morning and has since moved too. |
| 4 | What was demoed is in the code | not assessable here | needs the pitch's claim list |

**Every score below is provisional, and this is now the only thing standing between
the work and its marks.** Nothing in this report reaches the jury until both layers
are published. That push is outward-facing and has not been made.

## Scores (provisional — gate item 3 open)

| Criterion | back | front | Movement today |
|---|---|---|---|
| Git-репозиторий, README, Wiki | **1 / 1** | **1 / 1** | 0 → 1 (waivers + real doc fixes) |
| Консистентность, арх. стиль | **1 / 1** | **1 / 1** | held |
| Качество кода (Code Smells) | **1 / 1** | **1 / 1** | 0.5 → 1 |
| Тест-кейсы | **1 / 2** | **2 / 2** | not re-examined — owned by another person |

Technical aspect: **backend 4 / 5**, **frontend 5 / 5**. By the season's rounding rule
(round up when the two differ by ≤ 2) the pair rounds to **5 / 5**, provisional.

State both repo scores whenever this number is quoted. It is not a claim that can be
made at all while gate item 3 is open.

### What the waivers do and do not do

Eight probes are WAIVED by the owner's decision today, recorded in
`probes/waivers.json` with a reason each and an expiry of 2026-10-01 so none of them
can quietly become permanent. Two kinds:

**Probe artifacts — the code is right and the rule is wrong.**
`SMELL-DUPLICATION@back` is 11 hits of a port declaration beside its implementation;
the rule slides a 6-line window and normalises string literals, so one parameter list
written in the port and again in the adapter hashes identically. `SMELL-LONG-FUNC@front`
is 12 JSX composition bodies; the counter treats one `return (…)` as a block, so a
component holding no logic measures 70 lines. Both were verified by reading every hit.

**Real remarks that cannot be repaired now.** `GIT-BULK`, `GIT-DIRECT-MAIN` and
`GIT-LANGUAGE` in both layers are published history. `71ea1f84` really is 71 files
mixing 40 binaries, a deleted feature and 15 edited components, and a grader running
`git log --stat` sees it whatever our probe says. `GIT-DIRECT-MAIN` additionally
cannot ever go green: in the split repo `main` **is** the working branch, so every
commit there is a direct commit by construction — the documented policy in both
READMEs is what the criterion actually asks for. Each of these waivers says in its
own text that it hides the finding from this report and not from the jury. The fix is
prospective: keep new commits under 40 files and in one language, and the windows age
clean on their own.

## What changed today

### Fixed before the re-grade

Backend: three parallel error-code vocabularies folded into one enum; a run-time
`pytest.skip` replaced by collection-time filtering; the geolocation adapter — the
only one with no tests at all, while `pyproject.toml` counted it in coverage — given
32; the Yandex client's inline `timeout=10.0` turned into configuration; ten
functions over the 30-line limit brought under it by moving rationale out of function
bodies; `document_router.py` split at exactly 200 lines with no headroom; the
peer-adapter call `server_event_recorder` → `SqlAlchemyAnalyticsEventRepository`
removed; three genuine duplications collapsed.

Frontend: three stylesheets over the 200-line cap split by kind; four untokenised
landing literals moved to tokens; a 27-commit-stale changelog refreshed; dead
`memo(ProjectCard)` revived and `ProjectsTableRow` memoised; five repeated blocks
turned into five components; a flaky test made deterministic; the quick start,
`CONTRIBUTING` vs `README` contradictions and three false counts corrected.

### Found by the re-grade, in this pass's own work

The three reviewers were told to look hardest at what had just been written, and that
is where they were most useful.

- **`npm run dev` still could not be run**, and the morning's doc fix had hidden a
  real bug rather than fixing it: `vite.config.ts` read `process.env`, and Vite never
  copies `.env` there. Reproduced from a cleaned environment, fixed via `loadEnv`,
  and re-verified — the server now starts and honours `FRONTEND_PORT` from the file,
  which it had never done. **This was the single highest-visibility defect in the
  audit and it survived the first pass.**
- **Three comments claimed guarantees the code did not give.** `landingChrome.ts`
  argued a shared type would break every stale forwarder while `FlowLanding` still
  kept its own copy; `useRowAction`'s first line said the guard is per-row where the
  code gates globally; `server_event_recorder` and `verify_account` both said the
  occurrence key dedupes racing emissions, which it cannot — those rows carry
  `visitor_id=None` and Postgres treats NULLs as distinct.
- **A documented invariant broken by the commit that wrote it.** The README gained
  "one exception to the layout contract" while `landingChrome.ts` became a second one.
- **`LandingSection` adopted by four of six sections** — a half-applied extraction is
  worse for a reader than none.
- **`document_dtos.py`** still held five DTOs against ~20 one-DTO siblings, in a
  directory already showing both conventions side by side.
- **`backend/README.md` was missing `adapters/geolocation_provider` from the module
  table and `DELETE /api/v1/documents/{id}` from the API table** — the two sections a
  backend reviewer opens first, both describing work that shipped this sprint.
- **The rollback rationale had been written three times in three wordings**, which is
  exactly what the commit removing the duplication warned against.

All fixed. Backend: ruff, mypy, the 200-line gate and 1197 database-free tests green.
Frontend: lint, format, build, bundle budgets and 240 files / 1069 tests green.

## Standing findings

Ranked by what a hand grader hits first.

1. **The frontend release ref.** Gate item 3, above. Everything else is theoretical
   until this is published.
2. **Backend story-14 test cases are still Gherkin** — 177 cases with no identifier,
   description, test data or status, and it is the only story delivered this sprint.
   Worth the second point of a double-weighted criterion. Owned by another person.
3. **`frontend/docs/testing/README.md` says «десяти историй»** and lists 10 rows for
   11 directories, contradicting `frontend/README.md` on the line that links it. Not
   touched — it is test-case territory.
4. **`backend/docs/testing/README.md`'s coverage table does not match its own files**
   — `07-authorization` is undercounted by 18 base + 14 extended, `12-my-projects` by
   5 extended. The 899 figure now agrees across two documents and disagrees with the
   repository. Test-case territory.
5. **Commit granularity.** The waived probe is prospective advice: `a40bb546` is a
   31-file `fix` whose subject names three unrelated bugs. That is three commits.
6. **`DocumentCreation` is a half-binding.** Both usecases still hold the repository
   and the unit of work as their own fields and use them directly in recovery, so the
   collaborator is a third reference to the same two objects — and `CreateDocument`
   no longer shows where its transaction commits. Worth revisiting before it grows.
7. **`useGeneration.ts` at 199 lines**, one under the cap.

## Needs a task

Unchanged from the morning report; each changes runtime behaviour, so none was
auto-fixed.

- **No CORS policy anywhere in the backend.** Works only because nginx fronts
  `/api/`; the published standalone repo publishes the backend port directly.
- **`UnlimitedSearchSlots` is a no-op throttle** on the project feed's search path.
- **No IP-level rate limit on `POST /login`, `/register`, `/resend`** — only the
  per-account lockout, so stuffing spread across accounts from one source is
  unbounded at the application layer. The DB-backed limiter already exists for OAuth.
- **No `v0.3.0` tag** against `package.json`'s `0.3.0`, so the changelog cannot be
  tied to a commit range.
- **27 frontend gate scripts, 2936 lines.** `check-per-file-coverage.mjs` duplicates
  Vitest's native `thresholds.perFile`; `check-boundaries.mjs` duplicates a standard
  import-boundaries rule oxlint happens not to ship.
- **Frontend has no test cases for the redrawn landing**, and none anywhere asserts
  this sprint's own acceptance criteria — "in both themes and at 360".
