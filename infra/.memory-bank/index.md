# Memory Bank — index

> This is the source of truth for what the project is. The `/plan`, `/build`, `/review`,
> and `/debug` agents read this file FIRST.

## Project
- **What:** Infrastructure-as-code and delivery for the `textery` project (backend +
  frontend live in sibling `../backend/` and `../frontend/`, run under a separate
  continue-framework TDD loop — this `infra/` subtree is its own harness-managed project).
- **Goal:** Provision and operate the cloud resources both layers need (compute, state
  storage, secrets, CI/CD) safely and repeatably.
- **Stack:** Terraform (targeting Yandex Cloud — **unconfirmed, verify with the user
  before relying on `terraform-yandex` agent conventions**), Docker / docker-compose,
  CI/CD TBD.

## Where to look
- Architecture / modules → `./architecture.md` (not yet created — nothing provisioned yet)
- Decisions already made → `./decisions.md` (not yet created)
- Open questions → `./open-questions.md`:
  - Confirm target cloud provider (Yandex Cloud assumed from `terraform-yandex` agent —
    if wrong, swap for a different/generic IaC agent before running `/build`)
  - CI/CD platform not chosen yet
  - No resources provisioned yet — this is a fresh setup

(Create the files above as the project grows. Keep this index small — it is a table of
contents, not a dump.)
