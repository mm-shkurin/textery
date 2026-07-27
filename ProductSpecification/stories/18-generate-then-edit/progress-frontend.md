# Story 18: Generate → edit — Frontend Progress

Owns: Frontend Scenarios. Narrative/decisions/Spec checklist live in `progress.md`;
`ProductSpecification/stories.md` is the cross-file rollup.

This file tracks **which work units ran**.

## Frontend Scenarios (02_UI_Tests.md)

### Scenario 1.1: Selecting a type goes straight to generation
- [x] red-selenium — analytical RED (skipped; live run deferred to green-selenium). New `test_generate_flow_acceptance.py` (35) + `generate_flow_statements.py` (37) + conftest fixture. Asserts pick-doklad-type → `[data-testid='generation-generating']` visible AND `MODE_MODAL` NOT shown. Predicted RED: TimeoutException on `generation-generating` — current `useFlowNavigation.selectType` sets `step='mode'` (mode modal), no generating surface renders. New contract testid `generation-generating` (also 1.2's subject). test-review PASS 0 fixes. **Owed for green-selenium (non-gating, agent-review+premortem converge): (1) transient-surface flake — `assert_generation_started` waits on `generation-generating` with `live_session=True`; a fast real backend can transition past the generating state between polls → spurious TimeoutException indistinguishable from regression. green-selenium must pin generation to a deterministic pending window (slow/stubbed poll) before un-skip. (2) `assert_no_mode_modal_shown` (invisibility_of MODE_MODAL) passes vacuously for ANY modal-absent state (landing/error/editor) — only earns its keep because `assert_generation_started` runs first; coupled to (1). Consider adding a positive assertion that exactly one POST /generations fired (base DSL has `_count_requests_to`). Nit: redundant `element.is_displayed()` after `_wait_for_visible`.**
- [x] red-frontend — live vitest RED on `useFlowNavigation` hook seam. Added `it.skip` test: `selectType('doklad')` → `step==='form'` + `mode==='auto'` (straight to generation, no `'mode'` step). RED confirmed: `AssertionError: expected 'mode' to be 'form'` (useFlowNavigation.test.tsx:78) — current `selectType` sets `step='mode'`, `mode=null`. Matched prediction. test-review +1 fix: added `documentType==='doklad'` + `openDocumentId===null` (openDocumentId null is what makes ChatWorkspace POST a NEW generation vs GET existing). Suite 12 pass / 1 skip. **green note:** flipping `selectType` to `setStep('form')+setMode('auto')` breaks the existing "walks type then mode" test + makes `selectMode`/`backToModeModal`/`'mode'` step dead for the create path — handle in green/refactor. **Owed for green (agent-review+premortem, converge): (A, IMPORTANT) contract testid `[data-testid='generation-generating']` (used by red-selenium 1.1) does NOT exist — `ChatWorkspace.tsx` exposes `chat-panel`/`doc-area`, and `GenerationUiState` is `idle|pending|completed|failed` (no `generating`). green MUST reconcile: either add a `generation-generating` testid on the pending/generating surface, or repoint the Selenium locator to an existing testid + generation `pending` state. Also: at `step='form'&mode='auto'` the workspace renders `idle` unless `selectType` also triggers generation — pin that `form+auto` actually kicks off generation (renderer-level or Selenium), not just hook state. (B) `backFromEditor` for a new (non-history) doc falls through to `backToModeModal()`→`step='mode'` (now forward-unreachable but Back still routes there → orphaned modal); green must repoint Back + remove/retire dead `selectMode`/`backToModeModal`/`'mode'` wiring. Sibling tests `walks type then mode`, `returns a newly created document to the mode modal`, `unwinds the whole flow on sign-out` will break — green must preserve the sign-out poll-stop guarantee (add a single-step `selectType`-only logout-unwind test). (C) `mode` collapses to constant `'auto'` on create path — decide if generating-vs-editor should key off `openDocumentId` alone.**
- [x] green-frontend — `selectType` now sets `step='form'`+`mode='auto'` (straight to generation). Removed `selectMode`/`backToModeModal`/`'mode'` step; DELETED `ModeModal.tsx`/`.css`/test (dead). FlowLanding step narrowed to `landing|type`. `backFromEditor` (new/non-history doc) → `generation.reset()`+`step='type'` (history path unchanged → `history`). Added `data-testid='generation-generating'` on DocArea **pending** branch (contract A resolved by adding testid, not repointing locator). Siblings updated w/o weakening: removed `walks type then mode`; `...to mode modal`→`...to type step`; sign-out unwind converted to single-step `selectType`-only, poll-stop preserved. App.test.tsx integration updated (dropped 2 mode-modal→manual-editor entry tests; ManualEditor covered by own suite + history path). Suite **526 pass / 0 fail**, tsc clean. **CAVEAT (blocks green-selenium 1.1):** did NOT auto-submit generation at `form+auto` — `createGeneration` needs a real topic, none exists until composer used; workspace opens on idle composer, so `generation-generating` (pending) is not yet reachable on load. Auto-start + deterministic pending window owed to red-frontend-api/align-design BEFORE green-selenium 1.1 un-skips (remove-marker-only must not run prematurely).
- [~] red-frontend-api
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
