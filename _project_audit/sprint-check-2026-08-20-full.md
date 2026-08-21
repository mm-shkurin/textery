# /sprint-check — full (backend + frontend) — 2026-08-20

| | |
|---|---|
| Branch | `design/figma-alignment` |
| HEAD at probe time | `9f63a3f0` (report written at `e6bd5f10`) |
| Scope | full — both layers, Stage A + Stage B |
| Stage A final | backend **2.5 / 3.0** (iteration 13, confirmed) · frontend **2.5 / 3.0** (iteration 4, confirmed) |
| Probes | 64 PASS / 31 FAIL — back 16 (12 regression), front 15 (10 regression) |

## Stage 0 — the gate

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Deployed link exists and the app works | **PASS** | `README.md:7` names `https://mmshkurin.ru`, which answers 200; `/docs` 200, `/health` 200 |
| 2 | Every artifact in GitVerse | PASS | `gitverse-backend` / `gitverse-frontend` remotes configured, both `main` refs present and dated after 2026-08-14 |
| 3 | Release branch carries the sprint's work | **FAIL** | 20+ backend and 20+ frontend commits sit on `design/figma-alignment` and are absent from `gitverse-*/main` — including every fix in this report |
| 4 | What was demoed is in the code | not assessable here | needs the pitch's own claim list |

**Consequence: every score below is provisional.** Code is graded from the release
ref, and the release ref does not have this work. Pushing is outward-facing and was
not done — it needs an explicit decision, after reading
`git diff gitverse-backend/main..HEAD --stat` and the frontend equivalent.

## Scores (provisional — gate item 3 open)

| Criterion | back | front | Why |
|---|---|---|---|
| Git-репозиторий, README, Wiki | **0 / 1** | **0 / 1** | regression FAILs: back `DOC-ENV-CLEAN`, `DOC-CHANGELOG-FRESH`, `GIT-BULK`, `GIT-DIRECT-MAIN`; front `GIT-BULK`, `GIT-DIRECT-MAIN` |
| Консистентность, арх. стиль | **0 / 1** | **0 / 1** | back `ARCH-PATH-HACK`; front `ARCH-SIZE`, `ARCH-STATE-SPREAD`, `ARCH-SCOPED-STYLES`, `ARCH-DESIGN-TOKENS`, `ARCH-BOUNDARY-1` |
| Качество кода (Code Smells) | **0 / 1** | **0 / 1** | back five `SMELL-*` plus `TEST-SKIPS`; front `SMELL-MAGIC`, `SMELL-ENDPOINT-LITERAL`, `SMELL-POLLING` |
| Тест-кейсы | **1 / 2** | **1 / 2** | committed, complete per story, traceable — but the template carries only id/title/Given/When/Then |

Technical aspect: **back 1 / 5, front 1 / 5, rounded 1 / 5** (both repos equal, so the
rounding rule does not move it). Product aspect (pitch, UX/UI, USM) is outside this skill.

The single rule doing the damage: *any regression item not PASS → 0*. Nine of the twelve
criteria-1-to-3 slots would be 0.5 or 1 on new findings alone.

## Regression watch — the grader's own 2026-08-07 remarks

| ID | layer | status | evidence |
|---|---|---|---|
| `DOC-ENV-CLEAN` | back | FAIL | `backend/.env.example:80,83` — OAuth callback URLs still name `http://localhost/auth/callback` |
| `DOC-CHANGELOG-FRESH` | back | FAIL | 30 commits since changelog commit `a1781df4` (limit 25) |
| `ARCH-PATH-HACK` | back | FAIL | `backend/application/src/app/main.py:17-18` — `sys.path.insert` in the entry point |
| `SMELL-URL` | back | FAIL | `provider/gigachat_provider.py:18` — `TOKEN_URL` baked into source |
| `SMELL-FS-PATH` | back | FAIL | `provider/gigachat_provider.py:43` — `"russiantrustedca.pem"` resolved package-relative |
| `SMELL-MAGIC` | back | FAIL | `adapters/db/src/session.py:17` and eleven more module constants |
| `SMELL-POLICY-IN-CODE` | back | FAIL | `model/generation/generation_model.py:26` — `ALLOWED_STATUSES` in code |
| `SMELL-ENDPOINT-LITERAL` | back | FAIL | `middleware/no_store.py:33`, plus nine routers with literal `/api/v1/...` |
| `SMELL-TYPE-ESCAPE` | back | FAIL | `dto/auth/delete_account_request_dto.py:26` — `password: Any = None` |
| `TEST-SKIPS` | back | FAIL | `adapters/db/tests/conftest.py:30` — ~70 db tests skip on a fresh checkout |
| `GIT-BULK` | back+front | FAIL | `4f2d7873` — 44 backend / 56 frontend files in one commit |
| `GIT-DIRECT-MAIN` | back+front | FAIL | history, not fixable now — the policy is also undocumented in either published README |
| `ARCH-SIZE` | front | FAIL | `ProjectsPage.tsx` 212, `httpClient.ts` 205 (limit 200) |
| `ARCH-STATE-SPREAD` | front | FAIL | `VerifyCodeForm.tsx` 7 slots, `useFlowNavigation.ts` 4 (limit 3) |
| `ARCH-SCOPED-STYLES` | front | FAIL | `AccountLockedScreen.tsx:4`, `LoginForm.tsx` — global CSS imported by components |
| `ARCH-DESIGN-TOKENS` | front | FAIL | `OAuthCallback.css:18` — literal mask geometry beside declared tokens |
| `ARCH-BOUNDARY-1` | front | FAIL | `shared/api/send.ts:15` imports from `features/auth/` |
| `SMELL-MAGIC` | front | FAIL | `shared/formatCardDate.ts:33-34` |
| `SMELL-ENDPOINT-LITERAL` | front | FAIL | `shared/api/endpoints.ts:12` — `const V1 = '/api/v1'` |
| `SMELL-POLLING` | front | FAIL | `useGeneration.ts:139` fixed 5s interval; `AccountLockedScreen.tsx:39` 1s tick |

## New findings

Ranked by what a grader reading the repo cold hits first.

1. `SMELL-LONG-FUNC` — back `retry_generation.py:32` (65 lines), `generate_document.py:59`
   (65); front `ProfileMenu.tsx:39` (78-line block).
2. `SMELL-DUPLICATION` — back `document_storage.py:58` matches `document_repository.py:17`;
   front `FlowLanding.tsx:27` matches `LandingPage.tsx:30`.
3. `ARCH-SIZE-STYLE` — `ProfileMenu.css` 201 lines.
4. `GIT-LANGUAGE` — mixed Cyrillic/Latin commit subjects (back 11/49, front 4/56).
5. `GIT-BRANCH-NAMES` — `design/figma-alignment`, `gitverse-story-12-split` do not match the
   declared branch pattern.
6. Judgment — **backend runnability**: the README's «cp .env.example .env … заполнить
   POSTGRES_PASSWORD» named a variable the template did not carry, so
   `docker compose up --build` aborted on a fresh clone. **Fixed this run** (`e6bd5f10`).
7. Judgment — **frontend dead slice**: the whole `features/history` slice (~10 files,
   162-line `historyApi.ts`) has no route and no importer outside itself.
8. Judgment — **backend module cohesion / file naming**: `dto/document/document_dtos.py`
   holds five unrelated DTOs; `dto/auth/avatar_response.py` is the only sibling without the
   `_dto.py` suffix.
9. Judgment — **frontend peer chaining**: `projects`, `generation` and `profile` all import
   from `features/auth/`; the boundary script names the seam as an exception rather than
   removing it.
10. Judgment — **contribution distribution**: 494/8 backend, 605/7 frontend. Single-author
    history with no review signal, and no README section explaining the team split.
11. Judgment — **infrastructure portability**: TLS and the reverse proxy for `mmshkurin.ru`
    are hand-configured off-repo (`infra/architecture.md:98`); the compose stack's nginx
    listens on 80 only.

Disputed (auditor finding, checked and rejected): the backend README does document the test
run and `TEST_DATABASE_URL` — `README.md:170` and the «База для тестов `adapters/db`»
section at `README.md:200`.

## Fixed this run

| Commit | What |
|---|---|
| `c1e76a00` | Backend tip was red on its own gates: 216-line test file split, and a `conftest` import mypy cannot resolve replaced by the fixture the conftest publishes |
| `26890543` | Container ran as root and postgres was published on every interface — non-root `app` user, port bound to loopback |
| `4bc9380a` | Frontend tip was red on coverage (functions 97.41 to 98.17, branches 91.55 to 92.35) and on `format:check`; `shared/lib/browser.ts` and `ProfilePage`'s three exits got the suites they never had |
| `8e3b3b32` | The root backend workflow — the one that runs on monorepo pushes — carried none of the five gates and no coverage floor |
| `9f63a3f0` | Those gates ran on `main`/`dev` only while work lands on a working branch; plus `.mailmap` for the mistyped author address |
| `e6bd5f10` | `POSTGRES_PASSWORD` missing from `.env.example`, which broke the documented start |

## Not yet released

Everything above, plus the sprint itself. `gitverse-backend/main` = `97f19b59`,
`gitverse-frontend/main` = `219d4bbf`; both predate this branch's work. A fix that exists
locally and not on the release ref counts for nothing this sprint.

## Delta

No previous **full**-scope report exists — `sprint-check-2026-08-14-back.md` and `-front.md`
are single-layer and are not comparable by the skill's own rule. For context only, not
scored: the backend regression list is unchanged in composition since 08-14 except
`ARCH-TEST-DOUBLE-STANDARD`, which cleared; the frontend has since cleared `DOC-ENV-CLEAN`,
`ARCH-STATE-LIB`, `ARCH-ENV-ACCESS`, `SMELL-POLICY-IN-CODE`, `SMELL-REFETCH-TOKEN`,
`SMELL-TYPE-ESCAPE`, `DOC-CHANGELOG-FRESH` and `GIT-MESSAGES`.

## Needs a task

- **Test cases to 2/2** — the highest-value single move: 2 points, artifacts only, no
  production code. Add description, test data and a status column to the template, and
  concrete values in place of «refused as not found». 722 backend cases plus the frontend's.
- **Backend configuration extraction** — provider URLs, the certificate path, twelve module
  constants and the status allow-list move to configuration. Clears four regressions.
- **Backend route map** — one place naming `/api/v1/...`, consumed by nine routers and the
  no-store middleware.
- **`sys.path.insert` removal** — package the layer roots properly so the entry point needs
  no runtime path patching.
- **Frontend session layer out of `features/`** — removes `ARCH-BOUNDARY-1` and the peer
  chaining finding together, instead of listing them as boundary exceptions.
- **Frontend scoped styles and tokens** — component CSS through CSS modules; the literal
  mask geometry into the token sheet.
- **Generation progress off fixed-interval polling** — push, or back off.
- **`features/history`** — route it or delete it.
- **Documented direct-to-branch policy** — `GIT-DIRECT-MAIN` reads as a violation precisely
  because the policy lives in `.claude/rules/workflow.md`, which is in neither published
  repository.
