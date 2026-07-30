# Story 17: Export document — Carryover

Enduring quirks and invariants promoted from completed scenarios. Read by `/continue` on resume.

## Codebase Quirk: baked backend image must be rebuilt before acceptance runs
**Quirk:** The compose `backend` service runs a baked image (source copied in at build, no volume mount / reload), so freshly-committed backend code is invisible to a running container until it is rebuilt.
**Where:** infra/docker-compose.yml `backend` service.
**Implication:** Every green-acceptance / green-selenium step must `docker compose -f infra/docker-compose.yml up -d --build backend` and wait for a healthy recreate (~30s) before running the acceptance test — otherwise a correct green reads as RED against stale code.
**From:** scenario 1.1 (export-nonexistent-refused)

## Codebase Quirk: render adapters run in-container; importorskip needs the dep in requirements or it skips forever
**Quirk:** Render engines (weasyprint; and htmldocx/python-docx for docx) may be host-unimportable, so rendering-adapter tests use module-level `pytest.importorskip("<dep>")` and run in the Linux backend container. A `importorskip` whose dep is NOT in `backend/requirements.txt` (and installed on the CI runner) SKIPS FOREVER in the gating env — a vacuous green indistinguishable from a pass.
**Where:** backend/adapters/rendering (tests + Dockerfile + both CI ci.yml `test` jobs), backend/requirements.txt.
**Implication:** For any render dep, add it to requirements + both CI test jobs and confirm the suite actually RUNS (not skips) in CI; run red/green rendering-adapter tests in-container (`PYTHONPATH=domain/src:adapters/rendering/src:...`); never lift a RED skip into a permanent `skipif(unimportable)`.
**From:** scenario 2.1 (export-valid-pdf)

## Quirk: Selenium element.text reads whole-node subtree text
**Quirk:** Selenium `element.text` on a `data-testid` node returns the whole subtree's text, so an interactive child nested inside a message node pollutes an exact-text acceptance pin; unit-level `toHaveTextContent` matches substrings and does NOT catch it.
**Where:** ExportControl error banner; `manual_editor_export_error_statements.py` exact-text assertions.
**Implication:** Keep testid nodes that acceptance pins by exact text free of text-bearing children (put siblings in a wrapper); at unit level assert whole-node text with `.toBe(el.textContent?.trim())`, not `toHaveTextContent`.
**From:** scenario 3.2 (export-error)
