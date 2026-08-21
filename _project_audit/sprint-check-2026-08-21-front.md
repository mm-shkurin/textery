# Sprint check — frontend — 2026-08-21

- Branch: `feat/figma-alignment-with-analytics`
- HEAD at report time: `c06e06fd` (probes ran at `86f03d4b`; the formatting commit
  touches one test file and no probe input)
- Scope: `front` (frontend/, acceptance/tests/frontend/)
- Grading target: **working tree**. `--release` was NOT run; see Stage 0 item 2 — the
  release ref is so far behind that a release-ref probe run would grade last week's code.
- Stage A final: **2.5 / 3.0**, held (iteration 5: 3.0 → confirmation: 2.5)

## Stage 0 — the gate

| # | Gate item | Status | Evidence |
|---|---|---|---|
| 1 | Deployed link exists and works | **PASS (frontend)** | `README.md:7` publishes `https://mmshkurin.ru`; `GET /` answers `200`. `GET /api/health` answers `404` — that is the backend's gate item, not this layer's, and is named here only so it is not lost. |
| 2 | Every artifact in GitVerse and current | **FAIL — blocking** | `gitverse-frontend/main` = `219d4bbf`, dated **2026-08-14**. `git log --oneline 219d4bbf..HEAD -- frontend/` = **639 commits**. The whole sprint — analytics, CSS modules, the session move, the test cases published today — is absent from the graded repository. |
| 3 | Release branch carries the sprint's work | **FAIL — blocking** | Follows from 2. |
| 4 | What was demoed is in the code | not assessable here | Requires the demo; the code side is present in the monorepo. |

**Every score below is provisional under item 2.** A jury opening
`gitverse.ru/studentlabs/slide_frontend` on Friday grades the 2026-08-14 snapshot,
where the test cases do not exist, the analytics slice does not exist, and the README
still documents a default that would break its quick start. Pushing is the single
highest-value action left this sprint, and it is outward-facing: propose
`git diff gitverse-frontend/main..HEAD --stat`, show the deletions, and wait for the
user. It was not done by this run.

## Stage A — audit loop

| Iteration | Score | Note |
|---|---|---|
| 5 | 3.0 / 3.0 | before any fix this run |
| 6 | 2.5 / 3.0 | confirmation run, after the three fix commits |

Both are at or above the 2.5 target, so the loop closed on iteration 6 rather than
running to the cap. The confirmation run is the *lower* of the two and is what this
report carries — it is a fresh context that never saw the earlier one, and its lower
score comes from findings the first auditor did not raise (the unbounded `fetch` in
`analyticsClient`, the two over-cap profile test files, the malformed committer email),
not from anything the fixes broke.

Fixed inside the loop, one commit each:

- `c2bb0a4a` — the analytics slice had reinvented the storage guard the jury's
  `useDismissOnOutside` remark was about (`safely()` plus bare `window.localStorage`
  and `window.location` in three modules). It now goes through `shared/lib/browser.ts`,
  and `writeStored`'s boolean return **is** the visitor identity's `degraded` flag
  rather than a second guard beside it. `useProfileNameForm`'s four `useState`s
  describing one save attempt became one `SaveAttempt`. CHANGELOG entry added.
- `7519c91f` — story 14's 24 UI test cases rewritten into the executable eight-field
  template and synced into `frontend/docs/testing/14-analytics-event-tracking/`.
- `86f03d4b` — the README quick start made followable.
- `c06e06fd` — `format:check`, one of the eight CI gates, was red on HEAD.

Full iteration record: `frontend/AUDIT_LOG.md`.

## Stage B — per criterion

Scoring rule (`grading-rules.md`): any regression item not PASS → 0; regressions clean
with new findings → 0.5; all PASS/WAIVED → 1. This report covers one repository
(frontend); the backend repo is scored by its own run, and only then are the two
averaged and rounded.

| Criterion | frontend | Why |
|---|---|---|
| Git repo, README, Wiki | **0 / 1** | 2 regression FAILs (`GIT-BULK`, `GIT-DIRECT-MAIN`) |
| Consistency, architectural style | **0.5 / 1** | regressions clean; 2 judgment FAILs |
| Code quality / code smells | **0.5 / 1** | regressions clean; 2 new probe FAILs + 1 judgment FAIL |
| Test cases | **2 / 2** | 22 files, 252 cases + story 14's 24, all eight fields, in sync |

Probes: **45 PASS / 5 FAIL**, of which 2 are `regression: True`.
(2026-08-14: 29 PASS / 21 FAIL, 14 regression.)

### Regression watch

| ID | layer | status | evidence |
|---|---|---|---|
| GIT-BULK | front | FAIL | `4f2d7873` 56 files, `b8177512` 47, `d83f0e4a` 43, `ce767ac2` 41 (limit 40) |
| GIT-DIRECT-MAIN | front | FAIL | `d63c5598`, `60238586`, `b37e6d8e`, `d5b3ae68`, … landed on the integration branch directly |

Both are history. Neither can be fixed by editing a file, and rewriting the published
history is not a sprint-time action.

`GIT-DIRECT-MAIN` is **waiver material, not a defect**: the checklist accepts a
deliberate direct-commit policy *if it is documented*, and it is —
`frontend/README.md:237`, «Проект **не использует pull request'ы**: коммит — единственная
поверхность ревью». Adding the waiver is a human decision made outside a run
(`loop-rules.md`), so this run left it failing. Accepting it would move this criterion
from 0 to 0.5, since `GIT-BULK` would then be the only regression left — and `GIT-BULK`
is a real finding: `4f2d7873` "close the main USM and take the cheap half of MVP+" is
56 files across five unrelated features and is not revertible feature-wise.

### New findings

Ranked by what a grader reading the repo cold hits first.

1. **`analyticsClient.ts:59` calls `fetch` directly** instead of going through
   `shared/api/httpClient`, so an analytics report has no timeout at all — every other
   call in the product is bounded by `withTimeout`. `keepalive` is deliberate and
   documented; the missing bound is not. Architecture change → `## Needs a task`.
2. **Five per-feature error→Russian mappings, two incompatible error shapes.**
   `features/auth/api/apiError.ts:44` (an `AuthApiError` object) beside
   `shared/api/send.ts:33` `describeFailure` and typed `Error` subclasses, plus
   `projects/api/loadFailureMessages.ts:66`, `generation/hooks/saveFailureMessages.ts:34`,
   `shared/identity/api/profileErrors.ts`. There is a shared primitive but no single
   mapping; a future shared screen catching both must branch on shape, not type.
3. **`features/generation/components/` is a de-facto second `utils/`.** Seven
   non-component modules and a hook (`editorDomSync.ts`, `exportRun.ts`,
   `toolbarAction.ts`, `blockPlaceholder.ts`, `normalizeHref.ts`,
   `serializeEditorHtml.ts`, `editorToolbarActions.ts`, `useManualEditorInstance.ts`)
   while `generation/utils/` and `generation/hooks/` both exist; `shared/` likewise
   keeps `documentTypes.ts`, `textStyles.ts`, `volumePages.ts`, `formatCardDate.ts`
   loose at the slice root. The rule is honoured in `auth` and `projects` and abandoned
   here, so the same kind of file lives in three places.
4. **`SMELL-LONG-FUNC`** — 12 blocks over 30 lines, worst
   `ProjectRetryControls.tsx:26` (69), `ProjectsPage.tsx:31` (67),
   `ProjectsFeedSections.tsx:84` (57).
5. **`SMELL-DUPLICATION`** — 8 repeated 6-line blocks, the landing slice worst
   (`LandingAdvantages`/`LandingComparison`/`LandingCta` share one 5×).
6. **Thirteen `OAuthCallback.*.test.tsx` files** hand-copy the same
   `vi.mock('react-router-dom', …)` + `vi.mock('../../api/oauthExchangeApi')` preamble,
   while `src/test/renderWithRouter.tsx` already proves the shared-support pattern. A
   grader diffing two of those files sees it in seconds.
7. **The committer email on all 633 frontend commits is malformed** —
   `trape3977@g,ail.com`, with a comma. Visible in the first `git log` a grader runs,
   and it means the sole author's contribution cannot be attributed to a valid identity.
   Fixable going forward with `git config user.email`; the existing history is not.
8. **Bus factor 1** — `git shortlog -s -n -- frontend/` is 628 / 7, against a README
   that justifies the no-PR process as a two-person team's choice.
9. **`scripts/` is 27 files of gate infrastructure** against ~1.5k lines of application
   code, with no owner named. Each gate is individually justified and self-tested (that
   item PASSes), but the tooling now outweighs the product it guards.
10. **`scripts/check-audit.mjs` is fail-closed on npm registry reachability** with no
    offline cache — an npm outage turns every CI run and every local pre-commit gate red
    for a reason unrelated to the code.
11. **`GIT-LANGUAGE`** — 12 Cyrillic vs 48 Latin commit subjects; the repo has not
    settled on one.
12. Two test files over the 200-line cap: `useProfileNameForm.test.ts` (269),
    `useAvatarUpload.test.ts` (212). 12 loose assertions remain against 2033 `expect(`
    calls. 6 `any` casts remain under an otherwise strict config.
13. `useDocumentInit` cancels via a closure flag rather than the `AbortSignal`
    `httpClient` already supports, so an abandoned editor's request stays on the wire —
    inconsistent with the feed, which does pass `signal`.
14. `npm run testcases:check` and `npm run check:ingress` silently no-op in the
    published standalone repo, but the README lists them in the local gate list a
    standalone cloner would run.

### Delta — versus `sprint-check-2026-08-14-front.md`

Probes: **21 FAIL → 5 FAIL**; regressions **14 → 2**.

Fixed since (all 14 of last report's regressions, plus one new-found this run):
`DOC-ENV-CLEAN`, `DOC-CHANGELOG-FRESH`, `ARCH-STATE-LIB`, `ARCH-STATE-SPREAD`,
`ARCH-SCOPED-STYLES`, `ARCH-DESIGN-TOKENS`, `ARCH-ENV-ACCESS`, `ARCH-BOUNDARY-1`,
`SMELL-MAGIC`, `SMELL-POLICY-IN-CODE`, `SMELL-ENDPOINT-LITERAL`, `SMELL-POLLING`,
`SMELL-REFETCH-TOKEN`, `SMELL-TYPE-ESCAPE`, `DOC-TESTCASES`.

Regressed: none.

New this run: `SMELL-LONG-FUNC`, `SMELL-DUPLICATION` (both non-regression; both were
present before and are newly *reported* now that the louder failures are gone).

Criterion movement: git-docs 0 → 0 (different regressions), consistency 0 → 0.5,
smells 0 → 0.5, **test cases 0 → 2**. The last is the whole reason to push: it is worth
as much as the other two development criteria together, and on the release ref it is
still a 0.

## Needs a task

- **Bound the analytics transport.** Route `analyticsClient` through `httpClient` with
  a short timeout, or write down why the transport is deliberately not reused. Touches
  runtime behaviour on a fail-open path — not an auto-fix.
- **One error mapping.** Collapse the five per-feature code→message tables and the two
  error shapes into one. Cross-feature refactor.
- **Place the loose modules.** `generation/components/` and `shared/` slice root, per
  the layout the README declares and `auth`/`projects` follow.
- **Extract the OAuthCallback test preamble** into `src/test/`, alongside
  `renderWithRouter.tsx`.
- **Decide `GIT-DIRECT-MAIN`.** Either add the waiver (the policy is documented) or
  change the policy. A human decision, deliberately not taken by this run.
