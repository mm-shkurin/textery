# Sprint check — frontend — 2026-08-21

- Branch: `feat/figma-alignment-with-analytics`
- HEAD at report time: `c06e06fd` (probes ran at `86f03d4b`; the formatting commit
  touches one test file and no probe input)
- Scope: `front` (frontend/, acceptance/tests/frontend/)
- Grading target: **working tree**, which is now the same code as the release ref —
  `gitverse-frontend/main` was published from this branch and its tree is byte-identical.
- Stage A final: **2.5 / 3.0**, held (iteration 5: 3.0 → confirmation: 2.5)

## Stage 0 — the gate

Re-run after the publish; the original run's verdict is kept below it because a gate
that failed for most of the day is the thing worth remembering, not the minute it
started passing.

| # | Gate item | Status | Evidence |
|---|---|---|---|
| 1 | Deployed link exists and works | **PASS** | `README.md:7` publishes `https://mmshkurin.ru`; `GET /` answers `200`. `GET /api/health` answers `404` — the backend's gate item, not this layer's, named here only so it is not lost. |
| 2 | Every artifact in GitVerse and current | **PASS** | `gitverse-frontend/main` = `5fc76ef0`, 662 commits, tree byte-identical to `HEAD:frontend`; `git ls-tree -r` finds no `node_modules/`, `dist/` or `.env`. |
| 3 | Release branch carries the sprint's work | **PASS** | The 59 commits of this sprint are on `main` as 59 commits, not a dump. |
| 4 | What was demoed is in the code | not assessable here | Requires the demo; the code side is present. |

**How it was published, since the method is the finding.** The mirror is the
`frontend/` subtree with that directory as the repository root. Last sprint it was a
single squashed `chore(frontend): sync…` commit, and the jury took a mark off for
exactly that. This time: a throwaway clone, `python -m git_filter_repo
--subdirectory-filter frontend`, **4.6 seconds** — against the ~1.5 hours
`git subtree split` takes walking all 1756 monorepo commits.

The part worth writing down: `filter-repo` hashes are deterministic, and the previous
publish used it too, so all 603 already-published commits came out with the same
hashes and the mirror's head `219d4bbf` was an **ancestor** of the new history.
The push was a plain fast-forward — **no `--force`, nothing rewritten, no safety
branch needed**. The rewrite is paid for once; every later sprint is a fast-forward.

`feat/figma-alignment` was published the same way (`63de17f2`, 641 commits, tree
matching `feat/figma-alignment:frontend`) as a new ref, an ancestor of `main`.

**One anomaly, deliberately not fixed.** `refactor(usecase): five flows stop carrying
every step themselves` appears in the frontend history under a backend title: it
carries two zero-line frontend renames that the backend session's commit swept up.
The content is correct — the tree comparison is byte-exact — and rewriting published
history to retitle one commit costs more than it buys.

### Original verdict, 2026-08-21 morning — FAILED, blocking

`gitverse-frontend/main` was `219d4bbf`, dated **2026-08-14**, with the working tree
639 frontend commits ahead of it. The whole sprint — analytics, CSS modules, the
session move, the test cases — was absent from the graded repository, and every score
in this report was provisional under that until the publish above.

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

Scored twice: as the checklist pass found things, and again after the fixing session
that followed it. The second column is what is on the release ref.

| Criterion | at the pass | after fixes | Why it moved |
|---|---|---|---|
| Git repo, README, Wiki | 0 / 1 | **0 / 1** | unchanged — both regressions are history |
| Consistency, architectural style | 0.5 / 1 | **1 / 1** | both judgment FAILs fixed: module placement, one failure-text rule |
| Code quality / code smells | 0.5 / 1 | **0.5 / 1** | duplication 8 → 6 hits, but `SMELL-LONG-FUNC` stands (see below) |
| Test cases | 2 / 2 | **2 / 2** | — |

**Technical part, this repository: 3.5 / 5.**

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

Fourteen commits closed most of this list. Each entry says what happened.

**Fixed.**

1. ~~`analyticsClient.ts` called `fetch` with no bound~~ — `ef38cf56`. Now wrapped in
   `withTimeout` at a configurable 5s (`VITE_ANALYTICS_TIMEOUT_MS`), far below the
   product's 25s because nobody waits on telemetry. It stays on `fetch`: `keepalive`
   is what counts a visitor who closes the tab, and routing an analytics call through
   the shared client would put it inside the session's 401-renewal path. A timeout
   counts as `unreachable`, and the case is pinned by a test.
2. ~~Five per-feature error→Russian mappings~~ — `8bd7e66f`. The audit overcounted:
   three of the five are not mappings (`profileErrors.ts` declares error classes,
   `apiError.ts` is already the single normalization for auth, `loginErrorHandling.ts`
   is one screen's codes). The two that WERE the same rule — feed load and document
   save — now share `shared/api/failureText.ts`. Whether the server's words may reach
   the screen became an explicit per-screen choice; the save says no, because its
   sentence is an instruction and no 4xx wording carries it.
3. ~~`features/generation/components/` as a second `utils/`~~ — `bb6633d5`. Eight
   non-component modules and a hook left `components/`, six pure modules left
   `hooks/`, and in `shared/` the loose vocabulary modules became `shared/domain/`
   with `formatCardDate` joining `shared/lib/`. README describes the tree that exists.
4. ~~Thirteen OAuth suites hand-copying their preamble~~ — `dd62c516`. Ten of them,
   in fact; −112 lines, +27. `vi.mock` stays per file (the registry is per test file);
   everything those declarations point at moved to one support module.
5. ~~Two test files over the 200-line cap~~ — `12536a90`. Four files under it, split
   along seams already in them.
6. ~~12 loose assertions~~ — `00cb029a`. Two were worse than loose: `LandingHero`
   asserted something true by construction, `ProfilePage.recovery` asserted what
   `findByTestId` had already guaranteed by throwing.
7. ~~6 `any` casts~~ — none existed. The audit counted the word "any" in comments.
8. ~~`check-audit.mjs` fail-closed on registry reachability~~ — `1c7c6277`. Three
   attempts with backoff, still fail-closed. The same commit found the gate RED on
   HEAD (a stale ledger row) and its self-test toothless — it derived fixtures from
   the live ledger, so emptying that ledger silently killed two of its six cases.
9. ~~`useDocumentInit` cancelling by closure flag~~ — `56f785db`. The read is aborted;
   the create deliberately is not, because an aborted mutation leaves its outcome
   unknown.
10. ~~Landing duplication~~ — `aee21774`, `89a7ad58`, `668aa3b7`: one section head
    instead of six, one listener set instead of three, one retry picker instead of two.

**Standing.**

11. **`SMELL-LONG-FUNC` — 12 blocks over 30 lines, and I am not splitting them.**
    This is a threshold that does not fit React, not a defect. `useRetryGeneration` is
    already `attempt` + `retry`; `ProjectsFeedSections` carries a written reason why
    its four branches live together (exactly one can be on screen); a `useCallback`
    with a dependency array adds three or four lines to every function it wraps.
    Dividing further buys indirection and costs the reader.
12. **`SMELL-DUPLICATION` — 6 hits, largely probe artifact.** The rule normalizes
    string literals away (`probes/analysis.py:82`), so `styles['advantage-card']` and
    `styles['comparison-ours']` hash identically and any two `.map` rows over a card
    collapse into one "duplicate". The genuine ones were fixed above.
13. **The committer email on all frontend commits is `trape3977@g,ail.com`** — with a
    comma. Raised, and the owner chose to leave it; recorded here so the next run does
    not re-raise it as new.
14. **Bus factor 1** (628 / 7) and **27 gate scripts against ~1.5k lines of covered
    application code**. Both are now written down in `CONTRIBUTING.md` (`91fe93a3`),
    which also settles the commit-subject language the history was split on and the
    two gates that silently no-op in the standalone repo.

### Delta — versus `sprint-check-2026-08-14-front.md`

Probes: **21 FAIL → 5 FAIL**; regressions **14 → 2**.

All fourteen of last report's regressions are fixed, plus `DOC-TESTCASES`:
`DOC-ENV-CLEAN`, `DOC-CHANGELOG-FRESH`, `ARCH-STATE-LIB`, `ARCH-STATE-SPREAD`,
`ARCH-SCOPED-STYLES`, `ARCH-DESIGN-TOKENS`, `ARCH-ENV-ACCESS`, `ARCH-BOUNDARY-1`,
`SMELL-MAGIC`, `SMELL-POLICY-IN-CODE`, `SMELL-ENDPOINT-LITERAL`, `SMELL-POLLING`,
`SMELL-REFETCH-TOKEN`, `SMELL-TYPE-ESCAPE`.

Regressed: none. New: `SMELL-LONG-FUNC`, `SMELL-DUPLICATION` — both present before and
newly *reported* now that the louder failures are gone.

Criterion movement: git-docs 0 → 0, consistency 0 → 1, smells 0 → 0.5, **test cases
0 → 2**. The last was the whole reason to publish, and it is now published.

## Needs a task

Nothing from this run. The two items that were here — bounding the analytics
transport and collapsing the error mappings — were done rather than filed, and what
remains standing is either history that cannot be edited, a probe threshold that does
not fit the stack, or a decision the owner has already made.

## Verification at close

`npm run audit`, `lint`, `format:check`, `typecheck`, `test:coverage` all green.
1050 tests. Coverage 97.54 statements / 92.96 branches / 98.96 functions / 98.87 lines,
and the per-file floor passes across 260 files — it had gone red on this sprint's own
`attribution.ts` (64%) and `uuid.ts` (33%), which the aggregate at 96% was hiding.
