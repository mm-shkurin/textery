# /sprint-check — back (backend only) — 2026-08-21

| | |
|---|---|
| Branch | `feat/figma-alignment-with-analytics` |
| HEAD at report time | `1c7c6277` (probes run at `53bd172e`) |
| Scope | back — Stage A + Stage B, backend layer only |
| Stage A final | backend **2.5 / 3.0** (iteration 15, confirmed on two independent runs) |
| Probes | 38 PASS / 7 FAIL — 4 regression, 3 new (was 16 FAIL / 12 regression on 2026-08-14) |

## Stage 0 — the gate

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Deployed link exists and the app works | PASS | `README.md:7` names `https://mmshkurin.ru` — 200; `/docs` 200; `/health` 200 |
| 2 | Every artifact in GitVerse | PASS | `gitverse-backend` → `https://gitverse.ru/studentlabs/slide_backend.git`, ref present |
| 3 | Release branch carries the sprint's work | **FAIL** | `gitverse-backend/main` is at `97f19b59` (2026-08-14); **449 backend commits** on HEAD are absent from it, including every fix in this report |
| 4 | What was demoed is in the code | not assessable here | needs the pitch's own claim list |

**Consequence: every score below is provisional.** Code is graded from the release
ref, and the release ref does not carry this work. Pushing is outward-facing and
was not done — it needs an explicit decision after reading
`git diff gitverse-backend/main..HEAD --stat`.

## Scores (provisional — gate item 3 open)

| Criterion | back | Why |
|---|---|---|
| Git-репозиторий, README, Wiki | **0.5 / 1** | every `docs` probe PASS; the two remaining FAILs (`GIT-BULK`, `GIT-DIRECT-MAIN`) are history and cannot be repaired now |
| Консистентность, арх. стиль | **1 / 1** | every `arch`/`style` probe PASS; the judgment findings below are style drift, not boundary breaks |
| Качество кода (Code Smells) | **0 / 1** | regression `SMELL-MAGIC` and `SMELL-TYPE-ESCAPE` still FAIL |
| Тест-кейсы | **1.5 / 2** | 899 committed cases, complete and traceable to stories; story 14's 177 are still Gherkin, and no case names an automated test |

Technical aspect, backend repo: **3 / 5**, provisional. The frontend repo is scored
in its own report; the sprint number is the average of the two by the season's
rounding rule and cannot be stated from a single-layer run.

## Regression watch — the grader's own 2026-08-07 remarks

| ID | status | evidence |
|---|---|---|
| `DOC-ENV-CLEAN` | **PASS** | fixed earlier this sprint |
| `DOC-CHANGELOG-FRESH` | **PASS** | `CHANGELOG.md` records the analytics slice (`7253f22d`) |
| `ARCH-PATH-HACK` | **PASS** | `51885681` removed the nine `sys.path.insert` calls |
| `SMELL-URL` / `SMELL-FS-PATH` / `SMELL-POLICY-IN-CODE` / `SMELL-ENDPOINT-LITERAL` | **PASS** | moved to `*.toml` / `router/api_routes.py` in 0.2.0 |
| `TEST-SKIPS` | **PASS** | `8daf8a0a` — a missing test database fails the run |
| `SMELL-MAGIC` | FAIL | 7 sites, all from story 14: `analytics/client_context.py:28` (1024), `router/analytics/analytics_router.py:40` (16384), `container/analytics_wiring.py:46` (120), `domain/src/analytics/analytics_payload.py:25` (4096), `attribution.py:23` (200), `device.py:45` (4096), `language_tag.py:18` (512). The project moved every other limit into `limits.toml` / `gigachat_defaults.toml`; the new slice did not follow. |
| `SMELL-TYPE-ESCAPE` | FAIL | `dto/analytics/record_event_request_dto.py:28-30` and `dto/auth/register_request_dto.py:22-26` — `Any` on 8 fields. **Documented as a deliberate contract decision** (a strict annotation answers 422 echoing the rejected input on the only tokenless route). This is the one item where a waiver, not a fix, is the honest answer — and a waiver is the user's call. |
| `GIT-BULK` | FAIL | `eb35cafa` — 48 files, five layers, 2072 insertions |
| `GIT-DIRECT-MAIN` | FAIL | history; the policy itself is now documented at `backend/README.md:268-288` |

## New findings

Ranked by what a grader reading the published repo cold hits first.

1. **`pip-audit` is red on the tip** — `weasyprint==63.1` carries `PYSEC-2026-2034`
   and `PYSEC-2026-3412`, fixed in 68.0. A blocking CI gate fails today. Not fixed
   here: weasyprint is not installed on this machine (its PDF tests skip), so a
   version bump cannot be verified locally. See `## Needs a task`.
2. **`SMELL-LONG-FUNC`** — 11 functions over 30 lines, worst
   `usecase/src/analytics/record_analytics_event.py:75` (53) and
   `adapters/db/src/access/analytics/analytics_event_storage.py:22` (47).
3. **Two transaction-ownership conventions in one adapter layer** —
   `adapters/db/src/access/generation/generation_storage.py:53,108` self-commits;
   every other slice commits through the injected `UnitOfWork`.
   `access/document/document_storage.py:57` documents the divergence in a comment.
4. **Error codes: constants in two slices, raw literals in the rest** — 29 literal
   `error_code="…"` raises (`usecase/src/auth/register_user.py:67`,
   `usecase/src/document/save_document.py:110`) beside
   `usecase/src/analytics/analytics_error_codes.py`, whose docstring argues why
   literals are dangerous.
5. **Error-envelope inconsistency on `limit`** —
   `router/document/document_router.py:57` and `router/generation/generation_router.py:68`
   type the query param `int`, so `?limit=abc` returns FastAPI's `{"detail": …}` 422
   while `?limit=999` returns the canonical `INVALID_LIMIT` 400. The correct pattern
   already ships at `dto/project/project_page_params.py:29`.
6. **Public vs private collaborator fields split along story lines** —
   `usecase/src/document/save_document.py:36-38` vs
   `usecase/src/project/list_projects.py:23-25`. Reads as two authors.
7. **Port vocabulary drift: Repository vs Storage** — `DocumentRepository` port ↔
   `SqlAlchemyDocumentStorage`; `access/auth/account_storage.py:13` holds
   `SqlAlchemyAccountRepository`.
8. **`SMELL-DUPLICATION`** — the genuine pairs are
   `access/analytics/generation_visitor_storage.py:20` ↔ `oauth_attribution_storage.py:21`
   and `usecase/src/auth/resend_code.py:49-52` ↔ `verify_account.py:77-80`. The
   port-vs-adapter signature pairs the probe also reports are false positives.
9. **Test-fixture intimacy** — `usecase/tests/auth/oauth/test_complete_oauth_callback_usecase.py:66,101,110,146,165`
   asserts on `handoffs._by_value`, a fake's private storage.
10. **No case → automated-test traceability** — not one of 181 `test_*.py` files
    names a `TC-` id, and `docs/testing/README.md` carries no mapping table.
11. **`GIT-LANGUAGE`** — 25 Cyrillic vs 35 Latin commit subjects.
12. **Contribution distribution** — `git shortlog -sn -- backend/`: 447 vs 8, while
    `README.md:272` describes a two-person team.
13. **`.env.example` and the decisions table point out of the published repo** —
    `infra/architecture.md`, `ProductSpecification/decisions/…` are dead references
    in `slide_backend`.
14. **`check_file_size.py` gates `*.py` only** — `pyproject.toml` (231) and
    `ci.yml` (216+) exceed the project's own 200-line rule undetected.

## Fixed this run

| What | Commit |
|---|---|
| `mypy` was red at HEAD (`domain/src/analytics/attribution.py:53`) | `6fa73f0c` |
| `analytics_router._parsed` swallowed every `Exception` | `9695e826` |
| Three dead RED-phase `importorskip` guards | `84368ac5` |
| README claimed `--app-dir` is required for a `sys.path`-patching entry point | `b237493a` |
| The published repo's CI filtered `push` to `[main, dev]` — no sprint commit was gated | `bc6ffbfc` |
| `CHANGELOG.md` had not moved since 0.2.0 | `7253f22d` |
| README omitted the analytics endpoint, nine env vars, and promised skips where the db suite now fails | `e1a27f50` |
| Story 14 had **no test cases in the graded repo**; README counts were 579 vs 722 | `14d4b9a1` |
| The sync those copies depend on was gated by nothing | `ec6a1f36` |
| Dead factory `create_null_analytics_recorder` | `53bd172e` |

## Delta — versus `sprint-check-2026-08-14-back.md` (last back-scoped report)

- Probe FAILs: 16 → 7. Regression FAILs: 12 → 4.
- Fixed: `DOC-ENV-CLEAN`, `DOC-CHANGELOG-FRESH`, `ARCH-PATH-HACK`, `SMELL-URL`,
  `SMELL-FS-PATH`, `SMELL-POLICY-IN-CODE`, `SMELL-ENDPOINT-LITERAL`, `TEST-SKIPS`.
- Regressed: none.
- New: `SMELL-LONG-FUNC`, `SMELL-DUPLICATION`, `GIT-LANGUAGE` — all three are
  thresholds the analytics slice crossed, not previously-passing code that broke.
- Unchanged: `SMELL-MAGIC`, `SMELL-TYPE-ESCAPE`, `GIT-BULK`, `GIT-DIRECT-MAIN`.

## Needs a task

- **Bump `weasyprint` off 63.1.** Two known vulnerabilities, fix version 68.0, and
  a blocking CI gate is red on the tip. Needs an environment with the native
  Pango/cairo libraries so the PDF export suite actually runs against the new
  version — this machine skips it.
- **Move story 14's seven limits into configuration**, the way 0.2.0 moved every
  other one: the four domain bounds into `domain/src/shared/limits.toml`, the two
  transport bounds and the rate-limit default into an adapter-level TOML with env
  overrides, matching `gigachat_defaults.toml`. Clears `SMELL-MAGIC`.
- **Decide `SMELL-TYPE-ESCAPE`: waiver or refactor.** The `Any` fields are argued
  for in their own docstring. Either write `probes/waivers.json` with an expiry and
  an owner, or replace them with a permissive validator that keeps the envelope.
- **One transaction owner for the adapter layer.** `SqlAlchemyGenerationStorage`
  self-commits; move it onto the `UnitOfWork` the other slices use.
- **One error-code vocabulary.** Extend the `*_error_codes.py` module pattern over
  the 29 remaining literals.
- **Convert story 14's 177 cases to the six-field template** and run the sync.
- **Case → test traceability.** Name the `TC-` id in each automated test's docstring
  or carry a mapping table in `docs/testing/README.md`.
