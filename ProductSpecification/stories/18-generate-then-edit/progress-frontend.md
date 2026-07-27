# Story 18: Generate → edit — Frontend Progress

Owns: Frontend Scenarios. Narrative/decisions/Spec checklist live in `progress.md`;
`ProductSpecification/stories.md` is the cross-file rollup.

This file tracks **which work units ran**.

## Frontend Scenarios (02_UI_Tests.md)

### Scenario 1.1: Selecting a type goes straight to generation
- [x] red-selenium — analytical RED (skipped; live run deferred to green-selenium). New `test_generate_flow_acceptance.py` (35) + `generate_flow_statements.py` (37) + conftest fixture. Asserts pick-doklad-type → `[data-testid='generation-generating']` visible AND `MODE_MODAL` NOT shown. Predicted RED: TimeoutException on `generation-generating` — current `useFlowNavigation.selectType` sets `step='mode'` (mode modal), no generating surface renders. New contract testid `generation-generating` (also 1.2's subject). test-review PASS 0 fixes. **Owed for green-selenium (non-gating, agent-review+premortem converge): (1) transient-surface flake — `assert_generation_started` waits on `generation-generating` with `live_session=True`; a fast real backend can transition past the generating state between polls → spurious TimeoutException indistinguishable from regression. green-selenium must pin generation to a deterministic pending window (slow/stubbed poll) before un-skip. (2) `assert_no_mode_modal_shown` (invisibility_of MODE_MODAL) passes vacuously for ANY modal-absent state (landing/error/editor) — only earns its keep because `assert_generation_started` runs first; coupled to (1). Consider adding a positive assertion that exactly one POST /generations fired (base DSL has `_count_requests_to`). Nit: redundant `element.is_displayed()` after `_wait_for_visible`.**
- [x] red-frontend — live vitest RED on `useFlowNavigation` hook seam. Added `it.skip` test: `selectType('doklad')` → `step==='form'` + `mode==='auto'` (straight to generation, no `'mode'` step). RED confirmed: `AssertionError: expected 'mode' to be 'form'` (useFlowNavigation.test.tsx:78) — current `selectType` sets `step='mode'`, `mode=null`. Matched prediction. test-review +1 fix: added `documentType==='doklad'` + `openDocumentId===null` (openDocumentId null is what makes ChatWorkspace POST a NEW generation vs GET existing). Suite 12 pass / 1 skip. **green note:** flipping `selectType` to `setStep('form')+setMode('auto')` breaks the existing "walks type then mode" test + makes `selectMode`/`backToModeModal`/`'mode'` step dead for the create path — handle in green/refactor.
- [~] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 1.2: A generating document shows progress
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 2.1: A completed generation opens automatically in the editor
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 2.2: The auto-transition fires the conversion exactly once
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 2.3: The editor is populated from the conversion response, not a re-read
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 3.1: The generated document is editable and saves
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 4.1: A failed generation shows a distinct error, not a perpetual spinner
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 4.2: A conversion error keeps the text and offers retry
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 4.3: A transient poll error shows a distinct error, not a spinner
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 4.4: A generation that never finishes stops at the client deadline
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 5.1: Leaving with unsaved edits is guarded
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 6.1: A blank document can still be started from scratch
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 6.2: The converted document appears in history
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo
