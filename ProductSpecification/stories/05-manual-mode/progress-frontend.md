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
- [S] red-frontend-api — no API call: cursor-driven toolbar state is client-side editor state only, no backend endpoint involved
- [S] green-frontend-api — same reason
- [x] align-design — verify-only: no new markup/CSS for this scenario, reuses scenario 3.1's `.me-toolbar-btn[aria-pressed='true']` active-state styling already aligned to mockup 04-editor-content.html
- [S] green-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against. This is the deferred gap the premortem flagged (see red-frontend note above) — must run before 3.2 is fully verified.
- [S] demo — same reason, no live backend to drive a visible Selenium run against

### Scenario 4.1: Saving shows a loading state and disables the save control
- [S] red-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [x] red-frontend
- [x] green-frontend
- [x] red-frontend-api
- [x] green-frontend-api
- [x] align-design
- [S] green-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [S] demo — same reason, no live backend to drive a visible Selenium run against

### Scenario 4.2: A save completing out of order still reflects the latest edit, not a stale response
- [S] red-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [x] red-frontend — design decision (confirmed with user): out-of-order display is guarded by a queue/auto-retrigger mechanism, not a relaxed concurrent-save lock. Save button stays disabled while a save is in flight; a save requested during that window sets a "save again" flag, consumed automatically once the in-flight save settles, firing a new save with the then-current content and the version returned by the settled save. Saves stay strictly sequential (never more than one in flight), so no client-side sequence-number comparison is needed to resolve out-of-order responses. **Reinterpretation note (agent-review):** this makes the literal race in the gherkin ("first save's response arrives after the second save's response") structurally impossible rather than resolving it after the fact — a stronger guarantee that still satisfies the acceptance intent (displayed status never reflects a stale save), but does not exercise two genuinely concurrent in-flight requests. Accepted as the correct approach; noted so it isn't mistaken for a literal match at demo/QA time.
- [x] green-frontend — implemented in `ManualEditor.tsx`: `handleSave` now sets a `saveAgainRequested` ref (instead of no-op) when invoked while `isSaving` is true; the in-flight save's `.then()` consumes the flag and immediately fires `performSave` with the editor's current content and the just-settled version. Reject path (premortem finding): on rejection the queued flag is cleared without auto-retry (out of scope: autosave-retry), and `isSaving` still resets to `false` so the button re-enables for a manual retry with the latest editor content (nothing lost, content lives in Tiptap state). Added a new reject-path test alongside the resolve-path test (both were exercised, not just the pre-existing resolve one). Structural fix: the save button's `onClick` moved to a wrapping `<span>` because a native `disabled` button never dispatches/bubbles a click in jsdom/React, which would make the "second click while disabled" queuing untestable; the `<button disabled>` itself is unchanged so `toBeDisabled()` assertions still hold. Also added `afterEach(() => vi.clearAllMocks())` to the test file — mock call counts were leaking across tests in this file (no per-test reset existed), causing this scenario's `toHaveBeenCalledTimes` assertions to fail only when run as part of the full suite. Full suite: 42/42 passed. Typecheck: clean.
- [S] red-frontend-api — no new API call: scenario 4.2 reuses saveDocument's existing PUT /api/v1/documents/{id} contract (already implemented/tested in scenario 4.1); the queue/auto-retrigger logic is client-side state only
- [S] green-frontend-api — same reason
- [x] align-design — verify-only: no new markup/CSS for this scenario, reuses scenario 4.1's `isSaving`-driven `.me-save-btn[aria-disabled='true']`/`.me-save-spinner` styling; queued saves surface through the same visual state
- [S] green-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against. Real-browser click-suppression risk on the disabled/aria-disabled button was already reviewed and fixed via aria-disabled during green-frontend refactor — but this is still the only test type that can confirm the queue actually fires on a real browser dispatch; do not treat 4.2 as fully verified until it runs.
- [S] demo — same reason, no live backend to drive a visible Selenium run against

### Scenario 5.1: A successful save shows a lightweight confirmation, no full-page transition
- [S] red-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [x] red-frontend — predicted `waitFor` timeout looking for "Сохранено" text (no third save-status state exists yet, only draft/creating); actual matched exactly. Also strengthened via test-review to assert `onBack` never fires (real "no navigation" check) and post-save UI settles (aria-disabled=false, spinner gone).
- [~] green-frontend
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
