# Sprint check — frontend — 2026-08-14

- Branch: `features/story-13-profile-management`
- HEAD: `c7941331` (probes ran at `eb964863`, before the AUDIT_LOG commit)
- Scope: `front` (frontend/, acceptance/tests/frontend/)
- Grading target: **working tree**. `--release` was NOT run; see Stage 0 item 2.
- Stage A final: **3.0 / 3.0** (iteration 2: 2.5 → fix → iteration 3: 3.0, held)

## Stage 0 — the gate

| # | Gate item | Status | Evidence |
|---|---|---|---|
| 1 | Deployed link exists and works | **UNVERIFIABLE — blocking** | No public URL anywhere in the repo: `README.md`, `frontend/README.md`, `ProductSpecification/**`, `infra/**`. `infra/docker-compose.yml` declares Postgres/Redis/app ports for local dev only — no ingress, no host, no deploy target. |
| 2 | Every artifact in GitVerse and current | **FAIL** | `gitverse-frontend/main` = `696b241b`, dated **2026-08-07** — a monorepo sync. Nothing pushed since. Story-13 profile management, dark theme, the navbar unification and every fix from 2026-08-08…14 are absent from the graded ref. |
| 3 | Release branch carries the sprint's work | **FAIL** | Follows from 2 — the release ref predates the sprint's frontend work. |
| 4 | What was demoed is in the code | not assessable here | Requires the demo; the code side is present in the monorepo. |

A gate failure outranks every score below. Item 1 alone means the sprint scores 0 if
no working link is submitted; item 2 means the jury grades a week-old snapshot even
if a link exists.

## Stage A — audit loop

| Iteration | Score | Note |
|---|---|---|
| 2 | 2.5 / 3.0 | `lint` and `format:check` red on the branch tip |
| 3 | 3.0 / 3.0 | after `fix(profile): the delete modal announced a role instead of being one` |

Fixed inside the loop: `ProfileDeleteModal` is now a real `<dialog open>` instead of
`<div role="dialog">` (`jsx-a11y/prefer-tag-over-role` was failing `--max-warnings=0`),
`.profile-modal` resets `position/margin/color` because the UA sheet takes `dialog`
out of the scrim's flex centring; formatter run over the five files the previous two
commits left unformatted. Verified after: `npm run lint` green, 222 test files /
960 tests green.

Full iteration record, including the latent defects the 3.0 audit still listed:
`frontend/AUDIT_LOG.md`.

## Stage B — per criterion

Scoring rule (`grading-rules.md`): any regression item not PASS → 0; regressions clean
with new findings → 0.5; all PASS/WAIVED → 1. This report covers one repository
(frontend); the backend repo is scored by its own run, and only then are the two
averaged and rounded.

| Criterion | frontend | Why |
|---|---|---|
| Git repo, README, Wiki | **0 / 1** | 3 regression FAILs |
| Consistency, architectural style | **0 / 1** | 6 regression FAILs |
| Code quality / code smells | **0 / 1** | 6 regression FAILs |
| Test cases | **0 / 2** | the artifacts are not in the graded repo at all |

Probes: 29 PASS / 21 FAIL, of which 14 are `regression: True`.

### Regression watch

| ID | layer | status | evidence |
|---|---|---|---|
| DOC-ENV-CLEAN | front | FAIL | `frontend/.env.example:16: VITE_API_PROXY_TARGET=http://127.0.0.1:8100` |
| DOC-CHANGELOG-FRESH | front | FAIL | 26 commits since changelog commit `2ea09805` (limit 25) |
| GIT-DIRECT-MAIN | front | FAIL | `d63c5598`, `60238586`, `b37e6d8e` landed on the integration branch directly |
| ARCH-STATE-LIB | front | FAIL | no declared shared-state/data-cache solution |
| ARCH-STATE-SPREAD | front | FAIL | `VerifyCodeForm.tsx` 7 state slots, `useFlowNavigation.ts` 4, `useLoginSubmit.ts` 4 (limit 3) |
| ARCH-SCOPED-STYLES | front | FAIL | `LoginForm.tsx:10-11` global `./AuthForm.css`, `./AuthStatus.css` imports |
| ARCH-DESIGN-TOKENS | front | FAIL | `OAuthCallback.css:18-19`, `ChatWorkspaceDoc.css:47` literal mask geometry |
| ARCH-ENV-ACCESS | front | FAIL | `main.tsx:15`, `avatarImage.ts:64`, `useProjectView.ts:16` reach `document`/`window` directly |
| ARCH-BOUNDARY-1 | front | FAIL | `shared/api/send.ts:15`, `shared/identity/identityStore.ts:16`, `shared/components/profile/ProfileAvatar.tsx:1` import from `features/auth/` |
| SMELL-MAGIC | front | FAIL | `formatCardDate.ts:33-34`, `useResendCountdown.ts:8` |
| SMELL-POLICY-IN-CODE | front | FAIL | `avatarImage.ts:11: ALLOWED_AVATAR_TYPES = [...]` |
| SMELL-ENDPOINT-LITERAL | front | FAIL | `authApi.ts:25`, `loginApi.ts:62`, `oauthExchangeApi.ts:30` inline paths (identity layer uses constants — inconsistent within one codebase) |
| SMELL-POLLING | front | FAIL | `useGeneration.ts:148` fixed 5s interval, no backoff; `AccountLockedScreen.tsx:39` drifting 1s tick |
| SMELL-REFETCH-TOKEN | front | FAIL | `useProjectsFeed.ts:52: const [reloadToken, setReloadToken] = useState(0)` |
| SMELL-TYPE-ESCAPE | front | FAIL | `as unknown as` casts in `editorDomSync.guards.test.ts:28`, `ExportControl.download.test.tsx:33-34` |

`SMELL-POLLING` and `SMELL-REFETCH-TOKEN` are verbatim the 2026-08-07 remarks,
unremediated.

### New findings

Ranked by what a grader reading the repo cold hits first.

1. **Test cases are absent from the graded repo.** They exist and are current —
   `ProductSpecification/stories/{01,04,05,07,10,12,13,16,17,18}/tests/*.md`, this
   sprint's included — but that path is not inside the `frontend/` subtree pushed to
   `gitverse.ru/studentlabs/slide_frontend`. A jury reading GitVerse sees no test
   artifact. `DOC-TESTCASES@front` FAIL. Also untracked on disk:
   `Testing/Textery_Manual_Testing_Consolidated.xlsx`.
2. **The cases do not match the expected template even when found.** Pure Gherkin
   (`13/tests/02_UI_Tests.md:26`): no description, no preconditions naming an account,
   no typeable test data, no status column. Outcomes are unfalsifiable —
   `:53 "Then a defined loading placeholder is shown"`. Zero requirement references
   in `13/` or `18/` — folder placement is the only traceability.
3. **README's architecture section contradicts its own gate.** `frontend/README.md:49`
   names three `shared→features` exceptions; `scripts/boundaryRules.mjs` carries nine,
   and `shared/identity/api/identityRequest.ts` — a second token-attaching,
   self-renewing transport — is not in the documented HTTP stack at all.
4. **CHANGELOG stopped at 2026-08-07** (`2ea09805`); `[Unreleased]` still describes CI
   work while story-13, dark theme and the navbar unification went unrecorded.
5. **No memoization anywhere in `src`**, with search state held in the container
   (`ProjectsPage.tsx:43`) and threaded into the toolbar — every keystroke repaints
   the card grid and every `ProjectCard`. The 2026-08-07 known instance, still present.
6. **A disabled acceptance class and acceptance tests CI never runs.**
   `acceptance/tests/frontend/generation/test_auto_editor_transition_acceptance.py:31`
   is `@pytest.mark.skip` with a RED-phase reason; no workflow executes
   `acceptance/tests/frontend/**` on any push.
7. Loose assertions: `registerApi.test.ts:102 rejects.toBeDefined()` as the sole
   assertion in a test named for a specific message; `ProfilePage.recovery.test.tsx:63`
   `toBeTruthy()`; `useDocumentInit.strictMode.test.tsx:50`.
8. Unvalidated boundary input: `useProjectsFeed.ts:48 Number(params.get('page') ?? '1')`
   — `?page=abc` serializes `page=NaN` onto the wire (`projectsApi.ts:111`).
9. Size cap: `ProfileMenu.css` 201, `useProfileNameForm.test.ts` 269,
   `useAvatarUpload.test.ts` 212 (limit 200). Long blocks: `ProfileMenu.tsx:39` 78
   lines, `OAuthCallback.tsx:56` ~70-line effect, `ProfileAvatar.tsx:45` 56.
10. `documentApi.ts` holds four clients plus wire↔app naming, `parseVersion`
    validation and the 409 retry policy — one file, four responsibilities.
11. Duplication: `withBearer` byte-identical in `authorizedRequest.ts:22` and
    `identityRequest.ts:30`; the `400 → typed rejection` mapper written three times;
    the `busyRef` double-submit guard re-derived in three profile hooks; ~30 API test
    files hand-roll the same fetch stub and session `beforeEach`.
12. `GIT-LANGUAGE` — 4 Cyrillic vs 56 Latin commit subjects. `GIT-BRANCH-NAMES` —
    `gitverse-story-12-split` does not match the declared prefix scheme. File naming
    is loose at slice roots: `features/projects/` has no `hooks/`/`utils/` while
    `features/auth/` does; `features/generation/components/` mixes hooks and helpers
    in with components.

### Latent defects found by Stage A (not graded, but real)

- `useAccountDeletion.ts:44` compares the typed confirmation against `profile.email`,
  which `profileWire.ts:40` coerces to `''` when the field is missing — a malformed
  200 opens the irreversible button on empty input.
- `authSession.ts:66` can persist an access token without its refresh token and only
  returns the AND; `OAuthCallback.tsx` does not clear on `false`, so
  `isAuthenticated()` then reports true on a half-written session.
- Two renewal paths: `performRenewal` (`authorizedRequest.ts:54`) has a single-flight
  guard, `renewWithoutEndingSession` (`identityRequest.ts:43`) does not — two
  concurrent `/auth/refresh` when `GET /me` and `GET /me/avatar` both 401.
- `useDocumentInit.ts:68-111` applies the loaded document via
  `editor?.commands.setContent(...)`; if the fetch resolves first, the document
  renders blank. `useGeneratedDocumentInit.ts:59` guards with `if (!editor) return`.
- `ManualEditor.tsx:49` starts `hasUnsavedChanges = true` — a fresh blank editor
  triggers the beforeunload prompt.
- `safeRedirectTarget.ts` is dead: its only caller (`OAuthCallback.tsx:60`) passes
  `undefined`, so it can only return `'/'`.

## Delta

No previous `sprint-check-*.md` report exists — this is the baseline for the `front`
scope. The 2026-08-07 grader remarks are tracked as the `regression: True` probes
above; of those, `SMELL-POLLING`, `SMELL-REFETCH-TOKEN` and the unmemoized
per-keystroke re-render remain exactly as written then.

## Not yet released

Everything since `696b241b` (2026-08-07). The full frontend sprint output is
working-tree-only as far as the jury is concerned.

## Needs a task

- Publish the test-case artifacts inside the frontend GitVerse repo and rewrite them
  to the graded template (description, preconditions, typeable data, expected result,
  status, requirement reference). Largest single score movement available: 0 → 2.
- Extract a top-level `session/` module out of `features/auth/` so `shared/` stops
  importing from `features/` — removes `ARCH-BOUNDARY-1` and the nine boundary
  exceptions, and lets the README's three-layer HTTP description become true again.
- Declare a shared-state/data-cache solution, or record the deliberate decision not
  to, so `ARCH-STATE-LIB` is either PASS or WAIVED rather than silently red.
- Memoize the projects list and move search state out of the container.
- Route auth endpoint paths through one route map, matching the identity layer.
- Run `acceptance/tests/frontend/**` in CI and unskip (or delete) the disabled
  acceptance class.
