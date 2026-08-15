# Infrastructure

Always-on safety guardrails. The local-dev operational how-to (scripts, ports,
health checks), the CI-runner topology + slow-job diagnosis, and the load-test
infrastructure lifecycle live in `.claude/guidelines/infrastructure-detail.md` —
read it before starting/stopping services, touching CI runners, or running load tests.

## Infrastructure as Code

All infrastructure — local dev, prod-copy, production, certs, DNS, nginx config, observability, CI runners — is managed through files in the repository. The directory is `infra/`, never `infrastructure/` (the latter was a documentation-only name, corrected 2026-07-13; a stray `infrastructure/agent-progress.log` written by sub-agents against the old path was removed and the 16 agent files repointed on 2026-08-15). Read-only investigation is allowed; **state changes are not**.

- **NEVER make manual changes to remote infrastructure.** No SSH-and-edit on servers, no manual `certbot` runs, no clicking in cloud provider consoles, no ad-hoc `docker compose up` outside the repo's compose files, no DNS edits in a provider UI, no hand-tweaked nginx config on a host.
- **Three compose files, one owner each.** `infra/docker-compose.yml` (+ `infra/docker/`) is the monorepo's own orchestration and the default meaning of "infra change". `backend/docker-compose.yml` + `backend/Dockerfile` and `frontend/docker-compose.yml` + `frontend/Dockerfile` + `frontend/docker/` belong to the **published split repositories** — each must run standalone, cloned on its own, with no monorepo around it. They are edited as part of that repo's own build, not as an exception to this rule; keep the three in step when a shared thing (a base image, a port name, an env var) changes.
- **All other infra changes flow through `infra/`.** No Terraform/nginx-template/scripts subdirectories exist yet — if that kind of change is needed and no IaC source exists, propose adding one under `infra/` rather than editing anything by hand (see below).
- **When fixing infra, locate the IaC source first.** A broken cert, a misrouted hostname, a missing container — the symptom is on the running system, but the fix lives in the repo. Patch the source, never the running system. If you patch the running system "just to unblock", the next apply will overwrite your fix and the bug returns.
- **If no IaC source exists** for the thing you need to change, the fix is to create one — not to make the change manually. Stop and propose the IaC addition before proceeding.
- **Diagnosis is fine.** Reading certs (`openssl s_client`), checking DNS (`dig`), inspecting containers (`docker ps`, `docker logs`), tailing logs, even SSHing to look at something — none of these change state and are encouraged for investigation. The line is **looking vs. acting**.

## Destructive-Action Guardrails

Parallel repo instances and parallel Claude sessions share one host. These rules apply to **every** command you run, not only infra work:

- **NEVER hardcode port numbers** in skills, agents, or ad-hoc commands. All port config flows through `infra/.env` — always read from it.
- **NEVER kill processes by executable name.** This kills ALL instances system-wide, including other Claude sessions and user tools. Use the port-based stop scripts or kill only the specific PID you started.
- **NEVER remove Docker containers you didn't start.** Each session runs its own infrastructure containers. If `docker ps` shows containers with unexpected suffixes, they belong to another session — leave them alone. Only manage containers matching your own repo index (from `.env`).
- **NEVER run build daemon stop commands** for unknown processes — they kill ALL daemons system-wide, breaking test runs and backends in parallel Claude sessions.
