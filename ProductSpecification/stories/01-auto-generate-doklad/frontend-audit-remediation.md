# Frontend audit remediation (2026-07-10)

Direct remediation pass against `frontend/` findings from the external code-quality
grading prompt (`.memory-bank/sprint.txt`), done at the user's request **outside** the
normal story-scenario TDD lifecycle — no red/green ceremony, not tracked as
checkboxes in `progress.md`. Same spirit as the framework-skip decisions already
logged there, but triggered by a grading audit instead of sprint-deadline pressure.

**Score before → after:** 1.5/3.0 → 2.5/3.0 → 2.5/3.0 (re-audit) → target 3.0/3.0
(frontend-scoped audit runs, not re-scored after the fourth pass yet).

## What changed

Four commits on `dev`:

| Commit | Type | Summary |
|---|---|---|
| `4d56b72` | fix | cap `useGeneration` polling (`MAX_POLL_ATTEMPTS`), surface real API error detail in `generationApi.ts`, thread actual `volumePages` into `ChatWorkspace`, client-side topic length guard |
| `2459407` | refactor | extract `SelectableCard.tsx` (was duplicated across `TypeModal`/`ModeModal`), unify `DocumentType`/`DOCUMENT_TYPES` into `documentTypes.ts` (was a bare `'doklad'` string duplicated in `generationApi.ts`), split `LandingPage.css` (232→105 lines) into `LandingPage.css` + `LandingPageFeatures.css`, split `ChatWorkspace.tsx` (207→67 lines) into `Composer.tsx`/`Progress.tsx`/`DocArea.tsx` — both splits needed to satisfy the repo's 200-line file cap (`.claude/rules/coding-rules.md`) |
| `e88bc0a` | test | generation feature had **zero** test coverage before this — added `generationApi.test.ts`, `useGeneration.test.ts`, `ChatWorkspace.test.tsx`, `TypeModal.test.tsx`, `ModeModal.test.tsx`, `Header.test.tsx`, extended `LandingPage.test.tsx`; added `npm test`/`test:watch` scripts (vitest was configured, unused) |
| `73c801b` | docs | replaced unmodified create-vite boilerplate `frontend/README.md` with project-specific setup/env/test docs |

22 tests passing, lint/tsc/build clean at each step.

## Second pass (2026-07-10, same day) — remaining findings except CI

The score-2.5 review (frontend-only re-run of the grading prompt) surfaced four more
findings; user asked to fix all of them except CI. No new commit made yet in this
session — changes are in the working tree.

| File | Change |
|---|---|
| `Header.tsx` | removed the dead "Вход" button (`onClick` was never wired, no auth feature exists to wire it to) |
| `SelectableCard.tsx`, `Modal.css` | `add-btn` was a second `<button>` firing the exact same `onSelect` as the card — duplicate tab stop for one action. Changed to a decorative `<span aria-hidden="true">`; card itself stays the sole interactive target. CSS selector `.add-btn:disabled` → `.add-btn.disabled` to match (span has no disabled state) |
| `frontend/.env.example` (new) | documents `VITE_API_BASE_URL`, `VITE_API_PROXY_TARGET` (default matches `vite.config.ts`'s `http://127.0.0.1:8000` fallback), `FRONTEND_PORT` — previously only described in README prose |
| `.oxlintrc.json` | added `jsx-a11y` plugin + `no-unused-vars`, `no-console`, `react/exhaustive-deps`, `jsx-a11y/alt-text`, `jsx-a11y/anchor-is-valid`. Verified against `node_modules/oxlint/configuration_schema.json` (rule names differ from ESLint's, e.g. `react/exhaustive-deps` not `react-hooks/exhaustive-deps`) |

`npm run lint` (0 findings), `npm run test` (22/22), `npm run build` all clean after
the change.

## Third pass (2026-07-10, same day) — CI workflow

User clarified the frontend is already containerized via `infra/docker/frontend.Dockerfile`
+ the `frontend` service in `infra/docker-compose.yml` (both in this same repo, not a
separate infra repo — the two `gitverse-*` remotes are just split-repo mirrors, unrelated).
So the only remaining gap from the audit was the CI workflow itself; user approved adding it.

Added `.github/workflows/frontend-ci.yml`:
- `lint-test-build` job — `npm ci` / `npm run lint` / `npm run test` / `npm run build`,
  triggered on push to `main`/`dev` and on PRs, path-filtered to `frontend/**`.
- `docker-image` job (depends on the above) — `docker build -f infra/docker/frontend.Dockerfile .`
  from repo root, validating the existing image still builds; doesn't push anywhere.

Not routed through `infra/` IaC — GitHub Actions workflows are conventionally
`.github/workflows/`, not part of the docker-compose/Terraform IaC tree; this is the
standard location `.claude/rules/infrastructure.md`'s IaC principle maps to for CI.

## Fourth pass (2026-07-10, same day) — re-audit, score 2.5 → target 3.0

Re-ran the frontend-only grading prompt. Score 2.5/3.0. Six findings, user asked
to fix all six. Committed as `839fe0d` on `dev`.

| Finding | Fix |
|---|---|
| No CI typecheck step | Added `Typecheck` step (`npm run typecheck`, new `tsc -b --noEmit` script) to the existing `frontend-ci.yml` `lint-test-build` job — discovered mid-task that a CI workflow already existed untracked (`.github/workflows/frontend-ci.yml`, not yet committed by an earlier session); reused it instead of the duplicate `frontend.yml` first written, which was deleted |
| Dead `manual` generation mode (`ModeModal.tsx`, permanently `available: false`) | Kept — same "скоро" pattern as unavailable `DocumentType`s, and `ModeModal.test.tsx` already asserts the disabled state, so removing it would contradict the product's roadmap-preview convention. Added a comment on `App.tsx`'s `mode` state instead, noting it's UI-only until the backend accepts a mode parameter (confirmed via grep: no `mode` field anywhere in `backend/adapters/rest/src/dto/generation/`) |
| `DocArea.tsx` hardcoded `"создан только что"` regardless of actual generation age | New `formatRelativeTime.ts` (мин/ч/дн buckets); threaded real `createdAt` through `useGeneration` → `ChatWorkspace` → `DocArea`, replacing the hardcoded string |
| `DEFAULT_VOLUME_PAGES = 5` in `generationApi.ts` had no explanation | Added a comment: no page-count UI control exists yet, so every request is fixed at 5 pages until the product adds a selector |
| No test coverage for `App.tsx`'s `landing → type → mode → form` step machine | New `frontend/src/__tests__/App.test.tsx` — 3 cases: full forward walk, mode-modal back button, type-modal close-to-landing |
| — | `npm run typecheck`/`lint`/`test` (25/25)/`build` all clean before commit |

Also found and left alone: `backend/coverage_rest.xml` deletion was already staged
(pre-existing, unrelated to this pass) and rode along in the commit — flagged to
user, not undone since it was already the intended state of the index.

## Explicitly deferred (not done in any pass)

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
