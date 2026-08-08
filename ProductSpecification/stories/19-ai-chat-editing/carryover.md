# Story 19 — Carryover

Enduring quirks and decisions promoted from completed scenarios. Read on resume.

## Codebase Quirk: a ternary guard is invisible to --cov-branch

**Quirk:** `coverage.py` instruments `if`/`while` statements, not conditional expressions, so a guard written as a ternary reports `0/0 branches` — nothing measured, which reads identically to both arms proven.
**Where:** `backend/adapters/db/src/access/document_edit/ai_edit_storage.py`, and any ternary guard on this stack.
**Implication:** For a ternary, `--cov-branch` proves nothing; check the arms against named tests by hand.
**From:** scenario 1.2 (1-2-edit-of-another-document)

## Codebase Quirk: the coverage focus filter cannot see new files

**Quirk:** The tech template's coverage focus filter is `git diff HEAD --name-only`, which lists neither untracked paths **nor anything the RED commit already landed** — and on this project's cycle the ports always land in the RED commit.
**Where:** `.claude/tech/python-fastapi-hex/templates/testing/coverage-commands.md:38`.
**Implication:** Pass the filenames explicitly; `git status --porcelain` fixes only the untracked half. A clean focus report after any green phase is meaningless — four false all-clears so far on this story.
**From:** scenario 1.2 (1-2-edit-of-another-document), widened by scenario 1.3 (1-3-revision-of-another-document)

## Codebase Quirk: db test directories merge into the production namespace package

**Quirk:** `adapters/db/tests` is on `pythonpath`, so a test directory under `tests/access/...` merges into the same implicit namespace package as the production `access/` tree.
**Where:** `backend/adapters/db/tests/`.
**Implication:** A missing production module fails on the full dotted path, not the parent package — and a test-side module can shadow a production one by name.
**From:** scenario 1.2 (1-2-edit-of-another-document)

## Decision: guard acceptance tests wait for the paths they seed through

**Decision:** An acceptance test whose setup drives a real write waits for the scenario owning that write, rather than pulling it forward; such tests are re-scheduled at the tail of the backend sections so file order matches the intent.
**Why:** The next-work-unit rule is "first `[~]` or `[ ]` in file order", so prose saying "runs last" has no effect unless the position agrees.
**Where applied:** `progress-backend.md`, the Deferred entries above `## Integration Scenarios` (scenarios 1.1 and 1.2).
**From:** scenario 1.2 (1-2-edit-of-another-document)
