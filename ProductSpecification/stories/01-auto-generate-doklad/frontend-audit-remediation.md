# Frontend audit remediation (2026-07-10)

Direct remediation pass against `frontend/` findings from the external code-quality
grading prompt (`.memory-bank/sprint.txt`), done at the user's request **outside** the
normal story-scenario TDD lifecycle — no red/green ceremony, not tracked as
checkboxes in `progress.md`. Same spirit as the framework-skip decisions already
logged there, but triggered by a grading audit instead of sprint-deadline pressure.

**Score before → after:** 1.5/3.0 → 2.5/3.0 (frontend-scoped audit runs).

## What changed

Four commits on `dev`:

| Commit | Type | Summary |
|---|---|---|
| `4d56b72` | fix | cap `useGeneration` polling (`MAX_POLL_ATTEMPTS`), surface real API error detail in `generationApi.ts`, thread actual `volumePages` into `ChatWorkspace`, client-side topic length guard |
| `2459407` | refactor | extract `SelectableCard.tsx` (was duplicated across `TypeModal`/`ModeModal`), unify `DocumentType`/`DOCUMENT_TYPES` into `documentTypes.ts` (was a bare `'doklad'` string duplicated in `generationApi.ts`), split `LandingPage.css` (232→105 lines) into `LandingPage.css` + `LandingPageFeatures.css`, split `ChatWorkspace.tsx` (207→67 lines) into `Composer.tsx`/`Progress.tsx`/`DocArea.tsx` — both splits needed to satisfy the repo's 200-line file cap (`.claude/rules/coding-rules.md`) |
| `e88bc0a` | test | generation feature had **zero** test coverage before this — added `generationApi.test.ts`, `useGeneration.test.ts`, `ChatWorkspace.test.tsx`, `TypeModal.test.tsx`, `ModeModal.test.tsx`, `Header.test.tsx`, extended `LandingPage.test.tsx`; added `npm test`/`test:watch` scripts (vitest was configured, unused) |
| `73c801b` | docs | replaced unmodified create-vite boilerplate `frontend/README.md` with project-specific setup/env/test docs |

22 tests passing, lint/tsc/build clean at each step.

## Explicitly deferred (not done in this pass)

- **CI workflow** — user said "without infra for now" (2026-07-10). No
  `.github/workflows/` or `infrastructure/` CI runner pattern exists yet for
  `frontend/`; per `.claude/rules/infrastructure.md` this needs a proposed IaC
  addition, not an ad-hoc file, when it's picked up.
- **`.oxlintrc.json` rule expansion** — only 2 rules enabled
  (`react/rules-of-hooks`, `react/only-export-components`); no
  `no-unused-vars`/a11y/import-order rules. Not touched.
- **Git author-email typo** (`trape3977@g,ail.com` — comma instead of dot, visible in
  `git log` for several `frontend/` commits) — left alone; it's git config, not code,
  and out of scope without an explicit user request to change git config.
- **`ModeModal`'s `GenerationMode` union** has the same "duplicated-elsewhere" shape as
  `DocumentType` had, but nothing else currently references it — not unified since
  there's no second consumer yet (would be premature).

## Where this sits relative to the story

The touched files (`ChatWorkspace.tsx`, `useGeneration.ts`, `generationApi.ts`,
`TypeModal.tsx`, `ModeModal.tsx`, `LandingPage.tsx`) are all part of Story 1's
Frontend Scenarios (see `progress.md`), most of which were built framework-skip
(`[S]`) per the 2026-07-09 speed decision. This pass adds real regression coverage to
several of those `[S]`-marked areas retroactively (composer disabled-state,
type/mode-modal select/disabled behavior, landing CTA wiring) without reopening the
formal per-scenario checkboxes — the scenarios stay `[S]`, this doc is the record of
what got hardened anyway.
