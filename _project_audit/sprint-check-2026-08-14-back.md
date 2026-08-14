# /sprint-check — backend — 2026-08-14

| | |
|---|---|
| Scope | `--back` (backend/ only; frontend untouched) |
| Branch | `features/story-13-profile-management` |
| HEAD at report time | `feb67eff` |
| Stage A final score | **3.0 / 3.0** (iterations 10 → 2.5, 11 → 2.5, 12 → 3.0; log in `backend/AUDIT_LOG.md`) |
| Grading target | working tree (see `## Not yet released`) |

## Stage 0 — the gate: FAILED

Every score below is **provisional**. A failed gate scores the sprint 0 regardless
of code quality, and nothing in this report compensates for it.

1. **The release branch does not carry the sprint's work.** `gitverse-backend/main`
   is at `2f6e1f42 chore(backend): sync this repository with the monorepo's
   backend/`; 385+ backend commits on local HEAD are not on it, including every
   fix in this report. Code is graded from the release ref only.
2. **No deployed link is recorded anywhere in the repository.** Not in
   `README.md`, not in `backend/README.md`, not in `infra/`. `infra/` describes
   local development only — no production target, no hostname, no certificate
   config. The live check cannot be run from the repo.
3. Artifact remotes exist and are the right ones
   (`gitverse.ru/studentlabs/slide_backend`), but are stale per (1).

## Scores

Per `grading-rules.md`: any regression item not PASS → **0**; regressions clean
with new findings → 0.5; everything PASS or WAIVED → 1.

| Criterion | Backend | Why |
|---|---|---|
| Git-репозиторий, README, Wiki | **0 / 1** | `GIT-DIRECT-MAIN` (regression) FAIL |
| Консистентность, арх. стиль | **0 / 1** | `ARCH-PATH-HACK`, `ARCH-TEST-DOUBLE-STANDARD` (regression) FAIL |
| Качество кода (Code Smells) | **0 / 1** | six `SMELL-*` regressions FAIL |
| Тест-кейсы | **0 / 2** | `TEST-SKIPS` (regression) FAIL; no test-case documents in the published repo |

Frontend was not graded in this run, so no average is stated. Rounding applies to
the pair, not to one repository — `/sprint-check --front` before quoting a number.

Probes: 29 PASS / 16 FAIL (was 27 / 18). Closed this run: `ARCH-BOUNDARY-2`,
`TEST-TIMEOUT`.

## Regression watch (the grader's own 2026-08-07 remarks)

| ID | status | evidence |
|---|---|---|
| `ARCH-BOUNDARY-2` | **PASS** (fixed `07b4d886`) | MIME map moved to `adapters/rest/src/dto/document/export_media_type.py` |
| `TEST-TIMEOUT` | **PASS** (fixed `feb67eff`) | `adapters/db/tests/statements/race_timeout.py:22` |
| `ARCH-PATH-HACK` | FAIL | `application/src/app/main.py:17-27` — nine `sys.path.insert` calls |
| `ARCH-TEST-DOUBLE-STANDARD` | FAIL | `pyproject.toml:91` — `"**/tests/**" = ["ARG001", "ARG002"]` |
| `SMELL-URL` | FAIL | `provider/gigachat_provider.py:18-19`, `oauth_providers/yandex_oauth_provider.py:10-12` |
| `SMELL-FS-PATH` | FAIL | `provider/gigachat_provider.py:43` — `"russiantrustedca.pem"` |
| `SMELL-POLICY-IN-CODE` | FAIL | `sanitization/nh3_html_sanitizer.py:15,42,55,81` — inline allow-lists |
| `SMELL-ENDPOINT-LITERAL` | FAIL | nine routers with literal `/api/v1/...` prefixes |
| `SMELL-TYPE-ESCAPE` | FAIL | `dto/auth/delete_account_request_dto.py:26-27`, `update_profile_request_dto.py:41` |
| `SMELL-MAGIC` | FAIL | twelve module constants not sourced from configuration |
| `TEST-SKIPS` | FAIL | `adapters/db/tests/conftest.py:30`, `domain/tests/auth/test_email.py:33` |
| `GIT-DIRECT-MAIN` | FAIL | twelve commits landed straight on `main`; history, not fixable now |

Every remaining regression needs either a file outside `backend/` (the container
image, `infra/.env`) or a deployment decision — see `## Needs a task`. None was
force-fixed inside a single-layer run.

## Fixed this run

| Commit | What |
|---|---|
| `6bbd7f72` | `types` CI job was red: `DeleteAccount._confirmed` annotated in part |
| `d1aa309e` | `Cache-Control` missing on every error of `/me/avatar` and `/me/deletion` |
| `a1781df4` | README described the API of two stories ago; CHANGELOG missing story-13 |
| `d4c1eca2` | twelve `mypy` errors CI would have caught and nobody had run |
| `9d4f2530` | `scripts/check.py` — the gate list as one command |
| `07b4d886` | export usecase no longer names an HTTP media type |
| `65309bc7` | coverage measured the tests (94% real); `pip-audit` red on Markdown 3.7 |
| `feb67eff` | four race tests could hang instead of failing |

## New findings

Ranked by what a grader reading the repository cold sees first.

1. **No test-case documents in the published repository.** `ProductSpecification/
   stories/*/tests/` holds a full set per story (API, UI, Load, Infrastructure,
   Security, Integration) — none of it ships to `slide_backend`. The criterion is
   worth 0–2 and is currently graded against an empty directory. `DOC-TESTCASES`.
2. **README is not a repository-root README.** No containerization section, and
   it points at `infra/docker/backend.Dockerfile`, a path that does not exist in
   the published repo. No "create the application database" step (only the test
   one), no Python-version/virtualenv step, no licence. A reader following the
   three documented commands does not reach a running server — `YANDEX_CLIENT_ID`
   and `YANDEX_CLIENT_SECRET` are hard boot requirements even under
   `OAUTH_PROVIDER=fake`.
3. **`weasyprint 63.1` carries PYSEC-2026-2034 and PYSEC-2026-3412** (fix 68.0).
   The blocking `audit` job is red on it. Not bumped: weasyprint cannot be
   installed on this host, so a five-major-version jump on the PDF export path
   would ship unverified. Decision below.
4. **Env table drift**: `OAUTH_FAKE_AUTHORIZE_URL` is read by the code and listed
   in `.env.example` but missing from the README table; `TEST_DATABASE_URL` is in
   the table but absent from `.env.example`, which the README calls the full list.
5. **Two CI definitions.** The root `.github/workflows/backend-ci.yml` (the one
   GitHub actually runs) enforces none of lint/types/audit/coverage and still
   installs and waits on `redis-server`, which nothing in the tree reads. The
   gates live only in `backend/.github/workflows/ci.yml`, which runs in the split
   repo. Shared root file — not edited in a `--back` run.
6. **CI triggers exclude the branches the strategy relies on**: `push` to
   `main`/`dev` plus `pull_request`, and the project has no PRs, so `features/*`
   pushes run no gates at all.
7. **Transaction ownership differs between two adapters of one layer.**
   `generation_storage.py:30` commits inside itself; `document_storage` and
   `account_storage` only flush and leave the boundary to the usecase's
   `UnitOfWork`. Same layer, two persistence contracts.
8. **`generation_storage.py:121` mutates the caller's entity** (`generation.version
   = model.version`) after a CAS write; the sibling document storage returns a
   fresh entity instead.
9. `SMELL-LONG-FUNC` — twelve functions over 30 lines, worst
   `generate_document.execute()` at 64 (`usecase/src/generation/generate_document.py:58`).
10. `DOC-DECISIONS` — no decision record inside `backend/`; the ADRs live in
    `ProductSpecification/decisions/`, invisible to the published repo.
11. `GIT-LANGUAGE` — 18 Cyrillic vs 42 Latin commit subjects.
    `GIT-BRANCH-NAMES` — `gitverse-story-12-split` does not match the declared
    branch pattern.
12. `AUDIT_LOG.md` sits at the published repository root — an internal
    self-assessment journal at the same level as the README.

## Judgment lane — verdicts

Consistency: peer chaining PASS, composition root PASS, module cohesion PASS,
centralized error mapping PASS, no instance-local state PASS. **FAIL: file
naming** — `dto/document/` mixes `document_dtos.py` with `get_document_response_dto.py`,
and `dto/auth/avatar_response.py` (a `Response` factory) plus
`dto/project/project_page_params.py` (a query-string parser) sit loose among
`*_dto.py` siblings.

Smells: all seven judgment items PASS, including the SSRF the grader raised —
`weasyprint_pdf_renderer.py:38` installs a fetcher that refuses every outbound
URL. Largest class is `Account` with 9 public members; worst complexity is
`_webp_dimensions` at 8 flat branches.

Git/docs: commit granularity PASS, branching strategy PASS, test quality PASS
(788 of 876 assertions strict), coverage-in-CI now PASS after `65309bc7`.

## Needs a task

- **Publish the test cases into the backend repository.** Either sync
  `ProductSpecification/stories/*/tests/` into `backend/docs/testing/` at release
  time, or move the backend-facing ones there outright. 0–2 points ride on it.
- **Retire `sys.path.insert` from the entry point.** Declare the layer roots as
  packages (`[tool.setuptools.packages.find] where = [...]`) and install the
  distribution, so imports resolve without a runtime path patch. Touches the
  container image under `infra/docker/`, which a `--back` session may not edit.
- **Decide on `weasyprint` 68.0.** The bump closes two advisories and cannot be
  verified on this host; CI installs the native libs and runs the rendering suite,
  so CI is where it would be proven.
- **Provider URLs and the certificate path out of source.** Both are graded
  remarks. Moving them to environment variables means editing `infra/.env*`,
  which is shared.
- **One CI definition.** Make the root workflow either delegate to the backend one
  or enforce the same four gates, and delete the redis steps.
- **`DeleteAccount.execute` types both confirmations as `object`**, so the strict
  mypy pass covers nothing on the product's only irreversible operation. Narrowing
  to `str | None` means deciding what the DTO does with a malformed type first.

## Not yet released

Everything in "Fixed this run" exists only on
`features/story-13-profile-management`. Until it is pushed to
`gitverse-backend/main`, it counts for nothing this sprint.

## Delta

No previous `sprint-check-*.md` report exists — this is the baseline.
