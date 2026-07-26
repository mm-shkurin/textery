# Story 17: Export document to PDF / DOCX — Frontend Progress

Owns: Frontend Scenarios. Narrative/decisions/Spec checklist live in `progress.md`;
`ProductSpecification/stories.md` is the cross-file rollup.

This file tracks **which work units ran**.

## Frontend Scenarios (02_UI_Tests.md)

### Scenario 1.1: The editor offers a PDF and a DOCX export choice
- [x] red-selenium
- [x] red-frontend
- [x] green-frontend
- [S] red-frontend-api — control display is pure local toggle state; no backend call. The export endpoint (GET /documents/{id}/export) is exercised by scenario 5.1 (download).
- [S] green-frontend-api — same reason, no API for control display.
- [x] align-design — no mockup for story 17; styled to editor design tokens + defined the me-toolbar-row flex layout (breadcrumb left / export right). design-review PASS, coverage 100%.
- [x] green-selenium — real Chrome, 2 clean runs; against Vite dev :5273 + backend :8100 (no infra/.env on branch — run needs FRONTEND_PORT=5273 BACKEND_PORT=8100)
- [S] demo — autonomous loop, no interactive viewer; behavior already proven in real Chrome by green-selenium. Run `/demo TestExportControlDisplayAcceptance` manually to watch.

### Scenario 2.1: The export control is disabled while a request is in flight
- [x] red-selenium
- [x] red-frontend
- [~] green-frontend — **two review findings on the RED test (23ab6ce) to resolve here:** (1) *vacuous-pass risk (agent-review):* the RED test clicks the same captured `pdfOption` node twice; if green closes the menu on select, the 2nd click hits a detached node and passes with NO lock. Green must implement a real disabled/in-flight state on the control (per scenario title "control is disabled while a request is in flight") and the test must re-query + assert the control is disabled between clicks so the 2nd click reaches a live handler. (2) *lock-never-releases (premortem):* the never-settling mock can't prove release — add a sibling test with a manually-resolvable deferred asserting the control re-enables and a fresh click fires a 2nd `exportDocument` after settle (success AND reject paths; reject overlaps 3.2).
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium — **determinism debt (premortem 45e1e2b):** `trigger_export_as_pdf_twice` currently clicks twice with nothing holding the first `/export` open. Before relying on `== 1`, make the in-flight window deterministic — throttle the network (`Network.emulateNetworkConditions`) so the first request stays open AND wait for a browser-observable in-flight state (the exporting indicator from 3.1) before the second click. Mirror `manual_editor_save_queue_statements.py` (`_SLOW_LATENCY_MS` + `wait_for_save_in_flight`). Otherwise `== 1` passes a same-tick debounce (double-fire ships) or flakes on fast CI.
- [ ] demo

### Scenario 3.1: An in-flight export shows a progress state
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 3.2: An export error is shown with retry, document unchanged
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 4.1: Exporting with unsaved edits saves or warns first
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 5.1: A successful export delivers a downloaded file
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo
