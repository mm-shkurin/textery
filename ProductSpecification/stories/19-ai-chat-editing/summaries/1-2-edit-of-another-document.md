# Scenario 1.2: An edit belonging to another document of the same owner is not found

## red-usecase (2026-07-31)

**Mistake:** Marked the coverage step's green half `[S]` with the reason "no production change to make".
**Why wrong:** `/test-review` had demanded the bare `NotImplementedError` name itself, so a production change landed inside the red commit — the `[S]` condition (zero production files modified) was not met, and the no-red claim held for the raise but not for the message.
**Correct location/approach:** A `/test-review` fix that reaches into production makes the unit a red+green pair; mark the green step `[x]`, not `[S]`.

## red-adapter db (2026-07-31)

**Expected:** `ModuleNotFoundError: No module named 'access.document_edit'` — the parent package.
**Actual:** `ModuleNotFoundError: No module named 'access.document_edit.ai_edit_storage'` — the full dotted path.
**Why:** `adapters/db/tests` is on `pythonpath`, so a new test directory merges into the same implicit namespace package as the production `access/` tree and the parent resolves.
**Resolution:** None needed — the prediction was corrected. A test-side module can shadow a production one by name here.

## green-adapter db (2026-07-31)

**Quirk:** `coverage.py` instruments `if`/`while` statements, not conditional expressions, so a guard written as a ternary reports `0/0 branches` — nothing measured, which reads identically to both arms proven.
**Where:** `backend/adapters/db/src/access/document_edit/ai_edit_storage.py`, and any ternary guard on this stack.
**Implication:** For a ternary, `--cov-branch` proves nothing; check the arms against named tests by hand.

**Quirk:** The tech template's coverage focus filter is `git diff HEAD --name-only`, which never lists untracked paths, so any green phase that creates files rather than editing them filters to nothing and reports clean.
**Where:** `.claude/tech/python-fastapi-hex/templates/testing/coverage-commands.md:38`.
**Implication:** Pass the filenames explicitly, or use `git status --porcelain`; a clean focus report after a file-creating green phase is meaningless.

## green-acceptance (2026-07-31)

**Decision:** 1.2's acceptance is deferred to the tail of the backend sections rather than pulling its dependencies forward, applying the 2026-07-31 decision already made for 1.1.
**Why:** Its setup queues a real edit deliberately — a fabricated id is refused by any handler that merely fails to find it, so the path document id would never be consulted — which makes 3.1's `QueueAiEdit` and 4.x's state endpoint hard prerequisites.
**Where applied:** `progress-backend.md`, the Deferred entries above `## Integration Scenarios`.
