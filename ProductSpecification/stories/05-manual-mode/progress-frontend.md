# Story 5: Manual input mode (non-AI document creation) — Frontend Progress

Owns: Frontend Scenarios. Narrative/decisions/Spec checklist live in `progress.md`;
`ProductSpecification/stories.md` is the cross-file rollup.

**Policy (2026-07-15):** backend is developed in a parallel branch/session and is
unavailable on this branch. Every `red-selenium` / `green-selenium` / `demo` step
requires a live app to drive Selenium against — until backend is available here,
mark each as `[S]` with reason "backend unavailable on this branch (backend
developed in parallel session/branch); no live app to drive Selenium against" (or,
for `demo`, "same reason, no live backend to drive a visible Selenium run
against") the moment it becomes the next step, then continue to the next
backend-independent step (`red-frontend`, `green-frontend`, `red-frontend-api`,
`green-frontend-api`, `align-design`). Revisit this policy once backend is
reachable — the skipped scenarios' Selenium coverage still needs to run then.

## Frontend Scenarios (02_UI_Tests.md)

### Scenario 1.1: The mode modal now shows both modes as available
- [x] red-selenium
- [x] red-frontend
- [x] green-frontend
- [S] red-frontend-api — no API call: mode-modal availability is a static local flag, no backend endpoint involved
- [S] green-frontend-api — same reason, covered by red-frontend/green-frontend component tests
- [x] align-design
- [x] green-selenium
- [x] demo

### Scenario 1.2: Selecting Ручной режим opens the empty editor
- [x] red-selenium
- [x] red-frontend
- [x] green-frontend
- [S] red-frontend (coverage: document create succeeds, editor shows draft-not-saved status) — behavior already implemented in prior green-frontend; gap was a missing mock in App.test.tsx, not missing implementation. Closed by adding ManualEditor.test.tsx directly (passes immediately, no red phase).
- [S] green-frontend (coverage: document create succeeds, editor shows draft-not-saved status) — no implementation needed, see above
- [x] red-frontend-api
- [x] green-frontend-api
- [x] align-design
- [x] green-selenium
- [x] demo

### Scenario 2.1: A freshly created document shows an empty, ready-to-type editor
- [x] red-selenium — test added, already GREEN on first run: content placeholder, all 5 toolbar control groups, and no-skeleton were all built unconditionally by scenario 1.2's ManualEditor; no disable marker was needed since there was no red state.
- [S] red-frontend — fully covered by scenario 1.2's ManualEditor build, no new component logic required
- [S] green-frontend — same reason
- [S] red-frontend-api — no new API call for this scenario (display-only, document already created in 1.2's flow)
- [S] green-frontend-api — same reason
- [S] align-design — content-area/toolbar/breadcrumb styling already aligned to mockup in scenario 1.2
- [S] green-selenium — red-selenium test is already green; no marker to remove
- [x] demo

### Scenario 3.1: Applying a format changes the content and highlights the active toolbar button
- [x] red-selenium
- [x] red-frontend
- [x] green-frontend
- [S] red-frontend-api — no API call: bold formatting is client-side editor state only, no backend endpoint involved
- [S] green-frontend-api — same reason
- [x] align-design
- [S] green-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [S] demo — same reason, no live backend to drive a visible Selenium run against

### Scenario 3.2: The toolbar reflects formatting state at the cursor position, not globally
- [S] red-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [x] red-frontend — added cursor-move regression test (bold→plain); already GREEN, zero production changes. Covered by scenario 3.1's cursor-driven `isActive` + `shouldRerenderOnTransaction` + `syncNativeSelectionToProseMirror`. **Premortem CONCERNS (not yet resolved):** the jsdom test hand-fires the `select` DOM event via `fireEvent.select`, proving the handler logic but not that a real browser dispatches `select` for a caret-only (non-drag) cursor move — the deferred `red-selenium` for this scenario is the only test type that can close that gap; do not treat 3.2 as fully verified until it runs.
- [S] green-frontend — capability already provided by scenario 3.1, see red-frontend note
- [~] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 4.1: Saving shows a loading state and disables the save control
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 4.2: A save completing out of order still reflects the latest edit, not a stale response
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 5.1: A successful save shows a lightweight confirmation, no full-page transition
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 5.2: A failed save shows an inline error and keeps the content in the editor
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 6.1: "Назад" from the editor returns to the mode modal
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### Scenario 6.2: Reopening a previously saved document shows its saved content
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo
