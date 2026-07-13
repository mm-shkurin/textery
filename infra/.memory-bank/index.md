# Memory Bank — index

> This is the source of truth for what the project is. The `/plan`, `/build`, `/review`,
> and `/debug` agents read this file FIRST.

## Project
- **What:** Infrastructure and delivery for the `textery` project (backend + frontend
  live in sibling `../backend/` and `../frontend/`, run under a separate
  continue-framework TDD loop — this `infra/` subtree is its own harness-managed project).
- **Goal:** Right now, just local/Docker delivery — no cloud decided yet.
- **Stack:** Docker / docker-compose only, for now. **No cloud provider chosen** — decided
  2026-07-06. `terraform-yandex` and any other cloud-specific agent are **dormant**:
  installed (from labs-harness) but not applicable until a cloud is picked. Do not run
  `/build` against `.tf` files or assume Yandex Cloud from the agent's mere presence.

## Where to look
- Architecture / modules → `./architecture.md` — 5-service local-dev
  docker-compose topology (backend, worker, postgres, redis, frontend), port
  map, env var contract, and TEMP-placeholder callouts (backend/frontend have
  no real code yet).
- Decisions already made → `./decisions.md`:
  - `GIGACHAT_CREDENTIALS`/`GIGACHAT_CA_BUNDLE` (used by `backend/` for text generation,
    story 1) live in a local `.env` for now — updated 2026-07-13, provider switched from
    the originally-planned Anthropic/OpenRouter to GigaChat 2026-07-09 (see
    `.memory-bank/tasks/known-debt.md` #11; `infra/architecture.md` already had this
    right). Revisit (e.g. move to a cloud secret store) once a cloud provider is chosen;
    do not build any Lockbox/cloud-secret wiring before that.
- Open questions → `./open-questions.md`:
  - Cloud provider: not decided. When it is, confirm whether `terraform-yandex` applies
    (Yandex Cloud) or a different/generic IaC agent is needed.
  - CI/CD platform: resolved — `.github/workflows/{backend,frontend}-ci.yml` exist and
    run since 2026-07-10 (duplicated/diverged copies also exist under `backend/.github/`
    and `frontend/.github/`, see `_project_audit/05_CLEANUP_CANDIDATES.md` #8).

(Create the files above as the project grows. Keep this index small — it is a table of
contents, not a dump.)
