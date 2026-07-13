# Infrastructure — Detail

Deferred companion to `.claude/rules/infrastructure.md`. The rules file holds the
always-on safety guardrails (the IaC-as-source rule and the destructive-action
NEVERs); this file holds the local-dev operational how-to, the CI-runner topology
and slow-job diagnosis, and the load-test infrastructure lifecycle. Read it before
starting/stopping services, touching CI runners, or running load tests.

## Environments

| Environment | Purpose | Key files |
|-------------|---------|-----------|
| Local dev | Development, fixed ports (see below) | `infra/.env`, `infra/docker-compose.yml` |

## Local Development

> **Project-reality note (corrected 2026-07-13):** this section's template describes a
> per-instance port-isolation mechanism (`setup-ports.sh` generating `.env`, a `scripts/`
> directory, per-instance trap notes) that was never built for Textery. `infra/.env`
> holds fixed ports (`POSTGRES_PORT`/`REDIS_PORT`/`BACKEND_PORT`/`FRONTEND_PORT`, see
> `infra/architecture.md`) — there is no `infra/scripts/`, no `setup-ports.sh`, no
> `infra/notes/`. If you need to run parallel repo instances without port collisions,
> that mechanism does not exist yet and would need to be built, not just referenced.

All port configuration flows through `infra/.env` (fixed values, not per-instance
generated).

- **Starting/stopping services**: use the project's `/run-backend`, `/run-frontend`,
  `/stop-backend` skills — they read ports from `infra/.env` directly; there is no
  separate `infra/scripts/*.sh` layer to call into.
- **Health checks and curl calls** must read the port first, then check the health endpoint (see tech binding for the specific endpoint path).
- **If `infra/.env` is missing**, copy `infra/.env.example` — there is no generator script.

The destructive-action guardrails (never hardcode ports, never kill by name, never remove others' containers, never run build daemon stop) are in `.claude/rules/infrastructure.md`. Config files use fallback patterns. **Syntax differs by file type** — see tech binding for specific syntax per framework.

## CI Runners

CI topology (runner hosts, executors, autoscaling pools, job-tag routing) is project-specific — for Textery this is GitHub Actions (`.github/workflows/`) for the GitHub monorepo, plus mirrored workflows in `backend/.github/`/`frontend/.github/` that become the CI root for the GitVerse subtree-split repos (see `.memory-bank/steerings/development-conventions.md`). There is no separate `infrastructure/`-based CI IaC layer. The generic principles:

- **Check a runner pool's concurrency limit before adding a job to its tag.** Saturating a pool serialises every job sharing that tag — the symptom is large queue time while same-tag jobs run. Some pools are reserved for jobs that must not be preempted (infra apply/destroy, deploys, anything writing durable state); don't consume a scarce non-preemptible slot with a preemptible-safe job (unit tests, build, lint).
- **The IaC template is the source of truth for changes; the live config for diagnosis.** When investigating runner behaviour, read the live runner config first (it can drift from the template). When fixing capacity, update the IaC template *and* re-apply — never edit the server directly (per the IaC-as-source rule in the rules file).

### Diagnosing slow CI jobs

When a job is slower than expected, **attribute time to phases before changing the test or build script**. The runner is often the cause, not the code.

1. **Fetch the job trace** from the CI API and diff the section timestamps. Executor/VM-provisioning time vs actual script time tells you whether the slowness is runner-provisioning or your code — long prep + short script = a runner issue.
2. **If prep dominates, pull the runner journal** for the same window and look for cold-VM provisioning failures (SSH timeouts, cloud-API throttling during bulk VM cleanup). Warm-VM reuse collapses prep to a few seconds; a zero idle-count pool means the first job in a burst always pays the cold-start tax.
3. **Cross-check against other recent pipelines.** If the same job has been fast in other pipelines, the slowness is bursty (intermittent boot failure) — fix the root cause once, don't patch around it. If it's slow every time, it's a config issue (idle-count zero, missing build cache, etc.).

### Reproduce CI-only regressions locally first

A remote CI run is slow (often tens of minutes) and the runner is shared. When diagnosing a CI-only failure — especially a perf or environment-specific regression — attempt a local reproduction before iterating on the pipeline: run the same workload in a container constrained to a comparable shape (e.g. capped memory, similar disk class). Only fall back to a CI push when local genuinely can't reproduce it (CI may combine small RAM *and* slow disk that a fast local SSD won't). Don't default to "push and watch the pipeline" — that's the slow, contended path.

## Load-Test Infrastructure

The baked baseline Postgres container and the dedicated load backend are **ephemeral and resource-heavy** — the baseline container holds hundreds of thousands of rows and its autovacuum churns CPU even at idle. Unlike the dev backend and dev infra (meant to stay up across a session), load infra exists only for the duration of a load-testing session.

- **Cleanup is session-scoped, not run-scoped.** Iterative re-runs (TDD `green-acceptance` cycles) reuse the same warm load backend + baseline container — do **NOT** tear them down between runs. Re-baking or re-booting between runs is wasteful thrash.
- **When the load-testing session is finished, stop both:** the load backend (kill only the specific PID you started) and the baseline container (stop by name, matching your repo index). The never-kill-by-name and never-touch-others'-containers guardrails in the rules file apply unchanged.
