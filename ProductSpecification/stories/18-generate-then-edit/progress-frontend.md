# Story 18: Generate → edit — Frontend Progress

Owns: Frontend Scenarios. Narrative/decisions/Spec checklist live in `progress.md`;
`ProductSpecification/stories.md` is the cross-file rollup.

This file tracks **which work units ran**.

## Frontend Scenarios (02_UI_Tests.md)

### Scenario 1.1: Selecting a type goes straight to generation
- [x] red-selenium — analytical RED (skipped; live run deferred to green-selenium). New `test_generate_flow_acceptance.py` (35) + `generate_flow_statements.py` (37) + conftest fixture. Asserts pick-doklad-type → `[data-testid='generation-generating']` visible AND `MODE_MODAL` NOT shown. Predicted RED: TimeoutException on `generation-generating` — current `useFlowNavigation.selectType` sets `step='mode'` (mode modal), no generating surface renders. New contract testid `generation-generating` (also 1.2's subject). test-review PASS 0 fixes.
- [~] red-frontend
- [ ] green-frontend
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
