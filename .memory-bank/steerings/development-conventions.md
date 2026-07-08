# Development Conventions

## Methodology
TDD/ATDD + Clean Architecture, per continue-framework
(https://habr.com/ru/articles/1023094/, https://habr.com/ru/articles/1023998/):
strict red-green-refactor via `/continue`, ATDD chain (red-acceptance → red-usecase →
green-usecase → adapters-discovery → green-acceptance → frontend scenarios), mandatory
quality gates (test-review, coverage, refactor) before every commit. `progress.md` per
story is the persistence mechanism across context resets — this Memory Bank complements
it with cross-cutting facts, not story-level progress.

## Architecture
Clean Architecture, dependency flow strictly inward:
`backend/domain ← backend/usecase ← backend/adapters/{rest,db,...} ← backend/application`,
`frontend/` feature-based (Humble Object pattern), `acceptance/` black-box tests at top
level. Backend specifically follows Hexagonal Architecture (Ports & Adapters) — domain/
usecase define ports, adapters implement them. See [tech-details/backend.md](../tech-details/backend.md).

## Git
Revised 2026-07-07 (competition GitVerse/GitHub split, see below overrides the earlier
plain-GitHub-Flow note): `main` and `dev` branches. Feature work branches off the
current `dev` as `features/<slug>`, PRs back into `dev`. `dev` is the actively-moving
integration branch — pushed regularly, what gets deployed for Friday demos. `main` only
moves forward when `dev` is promoted (merge `dev` → `main`) at a deliberate "this is
stable" checkpoint — `main` is what mirrors to the customer-facing GitHub repo.
Commit messages: Conventional Commits prefixes — `feat:`, `fix:`, `chore:`, `refactor:`
(+ standard `docs:`/`test:` as needed) — short imperative summary, body only if the why
isn't obvious from the diff.

### Repos (competition constraint: grading only counts GitVerse)
- `gitverse.ru/studentlabs/slide_backend` — mirror of this repo's `backend/` subtree
  only, produced via `git subtree split --prefix=backend`. Needs its own
  self-contained `backend/README.md` (judges/automated audit read each GitVerse repo
  independently — no assumption they see this root repo's docs).
- `gitverse.ru/studentlabs/slide_frontend` — same, `--prefix=frontend`, own
  `frontend/README.md`.
- `github.com/mm-shkurin/textery` — this whole repo (all subdirectories), customer-
  facing only, **not graded**. Receives `main` only, not `dev`/`features/*`.
- Subtree-split mirrors are re-run before each Friday deadline (currently manual —
  `git subtree split --prefix=backend -b backend-mirror && git push <remote> backend-mirror:main`,
  repeat for frontend; worth scripting once this becomes routine).

## Scope split
- `backend/` + `frontend/` — continue-framework TDD loop, this shared `.memory-bank/`.
- `infra/` — separate harness-managed subtree (`/plan`/`/build`/`/review`/`/debug`), own
  `.memory-bank/index.md`, own `AGENTS.md`. Not part of the TDD loop above.

## Parallel sessions on one story: git worktrees, not one shared folder

Revised 2026-07-07. Running backend and frontend Claude Code sessions in the *same*
working directory is risky: they share one physical checkout, so one session's
in-flight (uncommitted) edits can land inside the other session's commit, or get
clobbered by it. Rule: **when two sessions need to work on the same story at the same
time, give each its own `git worktree`** — same `.git` object store (commits are
instantly visible to both, no push/pull needed), but separate working directory and
separate branch, so simultaneous edits can't collide.

Pattern used for story 1:
- Backend session: main checkout (`textery/`), branch `features/<slug>`.
- Frontend session: `git worktree add <sibling-path> -b features/<slug>-frontend
  features/<slug>` — a sibling folder, forked from the backend branch's current tip, own
  branch. Point the frontend Claude Code session's working directory at that sibling
  path, not at `textery/`.
- Both branches PR into `dev` **independently** when each is ready — no need to merge
  one feature branch into the other first.

**Syncing between them (manual, local, no network):** since it's one shared repo, pulling
one branch's state into the other is just a local merge, run from whichever worktree
needs the update:
```bash
# from the worktree that needs the OTHER branch's latest state
git merge features/<the-other-branch>
```
Do this when one side's work actually depends on the other's latest state — not on a
fixed schedule. Concretely for story 1: frontend builds against mocked API responses
(contract is already final in `endpoints.md`/OpenAPI specs), so it doesn't need
backend's code to progress at all until the point it's ready to swap mocks for the real
API — that's the natural moment to `git merge features/story-1-auto-generate-doklad`
into the frontend worktree. Until then, the frontend worktree's snapshot of backend
state (and of `progress.md`) is simply frozen at fork time — that's expected, not a
problem, since frontend's task doesn't depend on it.

Remove worktrees once merged into `dev` and no longer needed:
`git worktree remove <path>`.
