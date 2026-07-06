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
GitHub Flow: single `main` branch, short-lived feature branches, PRs before merging to
`main`. Commit messages: short imperative summary line + body explaining why.

## Scope split
- `backend/` + `frontend/` — one Claude Code session at project root, continue-framework
  TDD loop, this shared `.memory-bank/`.
- `infra/` — separate harness-managed subtree (`/plan`/`/build`/`/review`/`/debug`), own
  `.memory-bank/index.md`, own `AGENTS.md`. Not part of the TDD loop above.
