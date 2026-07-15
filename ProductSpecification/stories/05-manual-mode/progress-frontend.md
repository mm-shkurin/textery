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
- [x] green-frontend — implemented `hasUnsavedChanges` state (dirty check, not a one-way flag): true on any content edit, reset to false only when a save resolves with nothing queued. `.me-save-status` is now three-way: 'Создание документа…' / 'Сохранено' (doc + clean) / 'Черновик, ещё не сохранён' (doc + dirty). Added the required save→edit-again reversion test. Test file split (200-line limit): save-flow tests moved to new `ManualEditor.save.test.tsx`. Full suite: 44/44 passed. Typecheck: clean.
- [S] red-frontend-api — no new API call: confirmation display is client-side derived from saveDocument's existing response (already implemented/tested in scenario 4.1), no backend contract change
- [S] green-frontend-api — same reason
- [x] align-design — aligned dirty/saved status styling to mockups (04-editor-content.html: `--warning` color for dirty; 05-editor-saved.html: `--success` color + icon for saved), added `PlaceholderImage` as the icon stand-in per this project's established convention (no icon library, same pattern as breadcrumb chips). design-review: PASS. Coverage: clean.
- [S] green-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [S] demo — same reason, no live backend to drive a visible Selenium run against

### Scenario 5.2: A failed save shows an inline error and keeps the content in the editor
- [S] red-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [x] red-frontend — added failing test to new `ManualEditor.saveStatus.test.tsx` (split out of `ManualEditor.save.test.tsx` to stay under the 200-line limit): a rejected `saveDocument` call must render the mockup's exact inline error text (`06-editor-error.html`) and must not clear editor content. Predicted `TestingLibraryElementError: Unable to find an element with the text: ...` because the reject path only calls `console.error`/resets `isSaving` today with no error UI; actual failure matched exactly, and the DOM snapshot confirmed "hello world" stayed in `editor-content-area`. `it.skip` added with reason comment.
- [x] green-frontend — added `saveError` string state to `ManualEditor.tsx`, set on the `saveDocument` reject path with the mockup's exact inline error text, cleared to `null` on the next successful resolve; rendered in a new `.me-error-banner` element with `role="alert"` (ARIA live region so screen readers announce it) directly below the toolbar, editor content untouched (no code path clears it). Removed the `it.skip` marker. Addressed both premortem findings from red-frontend with dedicated tests: (1) `role="alert"` assertion added to the existing failed-save test; (2) new test "a stale error banner clears once a subsequent retry save succeeds" — reject once, click Save again with a resolved mock, assert the error text is gone and "Сохранено" shows. File-size fix: extracting the toolbar block (formatting buttons + save status + save button) into a new `ManualEditorToolbar.tsx` component kept `ManualEditor.tsx` at 172 lines (was heading to 206) and `ManualEditor.saveStatus.test.tsx` at 176 lines, both under the 200-line limit. Full suite: 47/47 passed. Typecheck: clean.
- [x] red-frontend-api — added `saveDocument rejects with server error detail on non-OK response` to `documentApi.test.ts` (no prior failure-path test existed for `saveDocument` specifically, only for `createGeneration`). Predicted PASS immediately: `saveDocument` delegates to the shared `request()` helper in `httpClient.ts`, which already throws on `!res.ok`, the same code path already proven by `createGeneration`'s failure tests. Actual: test passed on first run, no red state, no disable marker added. Full suite: 48/48 passed.
- [S] green-frontend-api — no production gap: `saveDocument`/`request()` already correctly rejects on non-OK responses, see red-frontend-api note
- [x] align-design — added `.me-error-banner`/`.me-error-banner-icon` CSS to `ManualEditor.css` matching mockup `06-editor-error.html` exactly (background `rgba(239,68,68,0.1)`, border-bottom `rgba(239,68,68,0.3)`, `color: var(--error)`, `padding: 12px 20px`, `font-size: 13px`, 16x16 icon), and added a `PlaceholderImage` icon inside the banner per this project's established icon-stand-in convention (no icon library). design-review: PASS. Coverage: clean, no follow-up needed (styling-only change, pre-existing `saveError` tests already exercise both banner render paths). Full component test file: 5/5 passed. Typecheck: clean.
- [S] green-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [S] demo — same reason, no live backend to drive a visible Selenium run against

### Scenario 6.1: "Назад" from the editor returns to the mode modal
- [S] red-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [x] red-frontend — added skipped test `App.test.tsx`: "back button from the manual editor returns to the mode modal, document type still scoped". Gap: existing `onBack` prop wired to `closeToLanding` (resets to landing, clears documentType/mode) instead of returning to mode modal with document type scoped. Predicted `TestingLibraryElementError: Unable to find [data-testid="mode-modal"]`; actual matched exactly (landing page rendered instead). test-review tightened aria-label assertion to exact string match. Suite: 4 passed, 1 skipped, 0 failed.
- [x] green-frontend — added `backToModeModal` handler in `App.tsx` (`setStep('mode'); setMode(null)`, documentType untouched), wired as `ManualEditor`'s `onBack` replacing `closeToLanding`. Removed `it.skip`. Full suite: 49/49 passed. Typecheck: clean.
- [S] red-frontend-api — no API call: "Назад" is client-side navigation state only (setStep/setMode), no backend endpoint involved
- [S] green-frontend-api — same reason
- [x] align-design — verify-only: no new markup/CSS for this scenario, reuses `.me-breadcrumb-back` styling already aligned to mockup in scenario 1.2; only the `onBack` handler's behavior changed
- [S] green-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [S] demo — same reason, no live backend to drive a visible Selenium run against

### Scenario 6.2: Reopening a previously saved document shows its saved content
- [S] red-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [x] red-frontend — added `ManualEditor.reopen.test.tsx`. Design decision (recorded per interview scope note: no document-list/history UI in this story, that's story #12): reopen is scoped at the `ManualEditor` component level via a new optional prop `existingDocumentId?: string`. When present, the component should call a new `getDocument(documentId)` API function (returning `{ documentId, status, content, version }`, matching `GET /api/v1/documents/{document_id}`) instead of `createDocument`, populate the Tiptap editor with the fetched `content`, and set `version` from the response so a subsequent save PUTs against the correct base version. Added a minimal `getDocument` stub (throws "not implemented yet") to `documentApi.ts` purely as a mock target for `vi.mock` automocking — no real fetch logic yet, that's `green-frontend-api`. Predicted `waitFor` timeout on `expect(documentApi.getDocument).toHaveBeenCalledWith('doc-99')` (component ignores `existingDocumentId`, always calls `createDocument`); actual matched exactly (editor rendered empty, only `ProseMirror-trailingBreak`). `it.skip` added with reason comment.
- [x] green-frontend — implemented real `getDocument` in `documentApi.ts` (GET, mirrors `saveDocument`/`createDocument`'s `request()` pattern) and wired `ManualEditor`'s mount effect to branch on `existingDocumentId`: calls `getDocument` and populates Tiptap via `editor?.commands.setContent(result.content)` + sets `version`, else falls back to `createDocument`. App.tsx wiring left untouched (no entry point in this story's scope). Removed `it.skip`. Full suite: 50/50 passed. Typecheck: clean.
- [x] red-frontend-api — added 2 tests to `documentApi.test.ts` for `getDocument` (success path + non-OK rejection), same pattern as `saveDocument`'s tests. No red state: `getDocument` was already implemented by green-frontend using the proven `request()` pattern, so both tests passed immediately (5/5 in file). No disable marker needed.
- [S] green-frontend-api — no production gap: `getDocument`/`request()` already correctly implemented, see red-frontend-api note
- [x] align-design — verify-only: no new markup/CSS for this scenario, reopen only populates the existing Tiptap editor/toolbar via `editor.commands.setContent`, which already renders through scenario 1.2/3.1's aligned styling
- [S] green-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [S] demo — same reason, no live backend to drive a visible Selenium run against

## Extended formatting toolbar (07_UI_Tests.md § 7, plan: ProductSpecification/plans/jazzy-stirring-key.md)

No mockup exists for scenarios 7.1-7.9 (extends past what the mockups spec) —
`align-design` notes reuse of `.me-toolbar-btn` styling unchanged instead of a
mockup comparison. All are client-side editor state, no backend involvement,
so `red-frontend-api`/`green-frontend-api` are pre-marked `[S]` for 7.1-7.8
(same pattern as scenario 1.1/3.1/3.2); 7.9 (Link) is left unmarked pending
`/design-preview` on the URL-input interaction. `red-selenium`/`green-selenium`/
`demo` are pre-marked `[S]` under this file's existing backend-unavailable
policy.

### Scenario 7.1: Applying strikethrough changes the content and highlights the active toolbar button
- [S] red-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [x] red-frontend — added skipped test to `ManualEditor.test.tsx`: strikethrough toolbar button (`data-testid="toolbar-strike"`) not yet implemented, no `strike` entry in `TOOLBAR_ACTIONS`. Predicted `TestingLibraryElementError: Unable to find an element by: [data-testid="toolbar-strike"]`; actual matched exactly. test-review: no loose assertions, no change needed.
- [x] green-frontend — added `strike` toolbar action to `editorToolbarActions.ts` (`toggleStrike()`/`isActive('strike')`, Tiptap StarterKit already bundles Strike extension), `data-testid="toolbar-strike"`. Removed `it.skip`. Also added a deactivation test (aria-pressed returns to false when cursor moves off struck text), mirroring bold/italic, closing the premortem gap flagged on the red commit. Full suite: 54/54 passed. Typecheck: clean.
- [S] red-frontend-api — no API call: formatting is client-side editor state only, no backend endpoint involved
- [S] green-frontend-api — same reason
- [x] align-design — verify-only: no new mockup/markup for scenario 7.x (per this section's header note); `ManualEditorToolbar.tsx` renders `TOOLBAR_ACTIONS` generically, strike button already uses shared `.me-toolbar-btn` styling. Build: clean.
- [S] green-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [S] demo — same reason, no live backend to drive a visible Selenium run against

### Scenario 7.2: Applying a blockquote changes the content and highlights the active toolbar button
- [S] red-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [x] red-frontend — added skipped test to `ManualEditor.test.tsx`: blockquote toolbar button (`data-testid="toolbar-blockquote"`) not yet implemented, no `blockquote` entry in `TOOLBAR_ACTIONS`. Predicted `TestingLibraryElementError: Unable to find an element by: [data-testid="toolbar-blockquote"]`; actual matched exactly. test-review: no loose assertions (strict `toBe`/`toHaveAttribute`), no change needed. Note for green phase: doc schema is `Document.extend({ content: 'inline*' })` — blockquote is block-level, may need schema adjustment beyond just adding the toolbar action.
- [x] green-frontend — implemented blockquote as a Tiptap `Mark` (`blockquoteMark.ts`), not the built-in Blockquote node: doc schema `content: 'inline*'` rejects mixed inline/block content, and reconfiguring Blockquote as an inline node caused ProseMirror DOM-diffing to inject stray empty `<blockquote>` tags on every keystroke (reproduced even without clicking the button). Mark-based approach mirrors Bold/Strike, avoids the schema conflict entirely. Added `blockquote` entry to `TOOLBAR_ACTIONS` (`toggleMark('blockquote')`/`isActive('blockquote')`), `data-testid="toolbar-blockquote"`. Corrected RED test's expected innerHTML: test only selects "hello" (offsets 0-5, same range as bold/strike), so real output is `<blockquote>hello</blockquote> world`, not the RED-phase guess of wrapping the whole string — verified against actual Tiptap output before correcting. Full suite: 55/55 passed, no regressions.
- [S] red-frontend-api — no API call: formatting is client-side editor state only, no backend endpoint involved
- [S] green-frontend-api — same reason
- [x] red-frontend-cursor-fix — added skipped test: cursor placed collapsed mid-word ("hello world", offset 3), click `toolbar-blockquote`, expect whole line wrapped (`<blockquote>hello world</blockquote>`), `aria-pressed="true"`. Predicted `AssertionError: expected 'hello world' to be '<blockquote>hello world</blockquote>'` (toggleMark no-op on collapsed selection); actual matched exactly. test-review: no loose assertions (strict `toBe`/`toHaveAttribute`), no change needed.
- [x] green-frontend-cursor-fix — `editorToolbarActions.ts` blockquote `run` handler now checks `editor.state.selection.empty`; when collapsed, resolves containing block start/end via `$from`, expands selection to block bounds with `setTextSelection`, then `toggleMark('blockquote')`. Ranged-selection path unchanged (other toolbar actions unaffected). Full suite: 56/56 passed, no regressions. Known open gaps (premortem, not covered by any test yet): cursor at line start/end boundaries, multi-line doc scoping, toggle-off via collapsed cursor on already-active blockquote.
- [x] red-frontend-selection-restore — added skipped test asserting `window.getSelection()` state after a collapsed-cursor blockquote toggle: cursor at offset 3 in "hello world", click `toolbar-blockquote`, expect `isCollapsed=true`, `anchorOffset=3`, `focusOffset=3`. Chose native-selection assertion over simulating a keystroke — this file's existing keystroke pattern overwrites `textContent` wholesale and can't distinguish "replaced" from "inserted" in jsdom; ProseMirror syncs its selection to the native DOM selection every transaction, so this exercises the same regression directly. Predicted `AssertionError: expected false to be true` (isCollapsed); actual matched exactly. test-review: strict `toBe` assertions throughout, no change needed.
- [x] green-frontend-selection-restore — `toggleBlockquote` captures `$from.pos` before expanding selection to block bounds; after `toggleMark('blockquote')`, chains `setTextSelection({from: cursorPos, to: cursorPos})` to collapse back. Marks don't change document structure so the captured offset stays valid post-toggle. Full suite: 57/57 passed, no regressions. Remaining open gaps (premortem, untested): restore after toggling blockquote off an active line, restore at boundary offsets (0/end-of-text), restore for the non-collapsed apply case; agent-review noted the test checks offset but not anchor/focus node identity.
- [x] align-design — verify-only: no mockup exists for scenario 7.x (per section header). `ManualEditorToolbar.tsx` renders `TOOLBAR_ACTIONS` generically; blockquote button already uses shared `.me-toolbar-btn` styling, no per-button CSS needed. Found and fixed unrelated build break during verification: prior refactor's test-file split left unused `documentApi` imports in two split files, failing `tsc -b` — fixed in a separate commit. Build: clean. design-review: PASS (static config array, no mockup placeholder data). test-coverage --focus: 100% line/branch coverage on scenario 7.2's own code (`toggleBlockquote`, `blockquoteMark.ts`); uncovered lines in `editorToolbarActions.ts` belong to other scenarios' toolbar entries, out of scope.
- [S] green-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [S] demo — same reason, no live backend to drive a visible Selenium run against

### Scenario 7.3: Inserting a horizontal rule adds a divider at the cursor position
- [S] red-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [x] red-frontend — new file `ManualEditor.horizontalRule.test.tsx` (per-scenario test file split pattern): horizontal-rule toolbar button (`data-testid="toolbar-horizontal-rule"`) not yet implemented, no `horizontalRule` entry in `TOOLBAR_ACTIONS`. One-shot insert, no toggle/active state (unlike bold/strike/blockquote) per spec wording. Predicted `TestingLibraryElementError: Unable to find an element by: [data-testid="toolbar-horizontal-rule"]`; actual matched exactly. test-review: tightened a `toContain('<hr>')` to exact `toBe('hello<hr>world')`, pinning insertion position.
- [x] green-frontend — doc schema is `Document.extend({ content: 'inline*' })`; Tiptap's stock `HorizontalRule` node is `group: 'block'`, incompatible. Implemented as a custom inline atom leaf node (`horizontalRuleNode.ts`, `group: 'inline', inline: true, atom: true`), not a mark (blockquote's approach doesn't fit a void leaf element). Found and fixed a real bug during implementation: an atom node with no required attrs becomes ProseMirror's schema `defaultType` filler — silently injected a blank `<hr>` on any doc mutation with no button click involved. Fixed via Tiptap's `isRequired: true` attr flag, which suppresses eligibility. Verified `editor.getHTML()` (the save path) also carries the `<hr>` through, addressing the premortem's silent-drop-on-save concern. `StarterKit.horizontalRule: false` disables the built-in block node. `horizontalRule` toolbar entry: one-shot `insertContent`, no active/toggle state. Full suite: 59/59 passed, no regressions.
- [S] red-frontend (coverage: parsing HTML with existing `<hr>` restores marker attr) — behavior already implemented in scenario 7.3's original green phase (`parseHTML: () => 'hr'`, `horizontalRuleNode.ts:40`); gap was a missing test, not missing implementation. New file `ManualEditor.horizontalRule.parseHTML.test.tsx` loads a document with existing `<hr>` content, asserts round-trip through `setContent`/`innerHTML` — passes immediately, no red phase. test-review: strict `toBe`/`toHaveBeenCalledWith` assertions, no change needed.
- [S] green-frontend (coverage: parsing HTML with existing `<hr>` restores marker attr) — no implementation needed, see above
- [S] red-frontend-api — no API call: formatting is client-side editor state only, no backend endpoint involved
- [S] green-frontend-api — same reason
- [x] align-design — verify-only: no mockup for 7.x scenarios (per section header); toolbar button rendered generically via `TOOLBAR_ACTIONS`, reuses shared `.me-toolbar-btn` styling. Build: clean. design-review: PASS (static config array, no mockup placeholder data). test-coverage --focus found a reachable gap: `horizontalRuleNode.ts:40` `parseHTML` (restores `marker` attr when reparsing `<hr>` from HTML — paste/undo/reload path) is untested; all existing coverage goes through the toolbar-click insert path only. Follow-up `red-frontend`/`green-frontend` coverage steps inserted above.
- [S] green-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [S] demo — same reason, no live backend to drive a visible Selenium run against

**Deferred coverage gaps (premortem on both green-frontend and the parseHTML coverage commit; not blocking, no tracked follow-up steps yet — reversible client-side editor-state risks, not data loss):** (1) consecutive `<hr>` nodes untested (`a<hr><hr>b` round-trip through save); (2) undo/redo interaction with the `isRequired` schema-filler fix untested — undo/redo replays transactions through the same content-matching path that produced the original ghost-filler bug; (3) `<hr>` insertion/parse at document start/end/as-sole-content untested. If any of these surface as real bugs later, open a bug task rather than reopening this scenario.

### Scenario 7.4: Applying inline code and code blocks changes the content and highlights the active toolbar button
- [S] red-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [x] red-frontend-inline-code — new file `ManualEditor.inlineCode.test.tsx` (per-scenario split pattern), mirrors bold/strike: apply test (select "hello", click `toolbar-code`, expect `<code>hello</code> world`, `aria-pressed="true"`) and deactivation test (cursor moves off coded text, `aria-pressed="false"`). No `code`/`inlineCode` entry in `TOOLBAR_ACTIONS`. Predicted `TestingLibraryElementError: Unable to find element [data-testid="toolbar-code"]` for both; actual matched exactly. test-review: strict `toBe`/`toHaveAttribute` throughout, no change needed.
- [x] green-frontend-inline-code — StarterKit's built-in `Code` mark was still enabled (not disabled in `StarterKit.configure(...)`, unlike Blockquote/HorizontalRule), so no custom mark file needed — just added `code` entry to `TOOLBAR_ACTIONS` using `toggleCode()`/`isActive('code')`. Fits `content: 'inline*'` cleanly, no schema conflict (as expected for a mark). Full suite: 61/61 passed, no regressions. **CONFIRMED (verified directly, not speculative):** Tiptap's stock `Code` mark ships with `excludes: '_'` (`node_modules/@tiptap/extension-code/dist/index.js:42`), meaning applying code to a bold selection silently strips the bold mark — reproduced via a throwaway test: bold "hello" then code → `<code>hello</code> world` (no `<strong>`). Out of scope for this scenario's Gherkin spec (7.4 doesn't test mark combination) and may be intended default behavior for code spans in many editors — not fixed here, but flagged as confirmed so a bug task can address it if the product wants bold-preserved-inside-code. Also deferred (premortem, untested): collapsed-cursor no-op, partial-overlap-selection.
- [x] red-frontend-code-block — new file `ManualEditor.codeBlock.test.tsx`: collapsed cursor (offset 3, "hello world", no selection) on `toolbar-code-block` click, expect whole line wrapped `<pre><code>hello world</code></pre>`, `aria-pressed="true"`. Correctly scoped as cursor-only per spec (test-review verified: true collapsed range, not selection). Predicted `TestingLibraryElementError: Unable to find element [data-testid="toolbar-code-block"]`; actual matched exactly. test-review: strict `toBe`/`toHaveAttribute`, no change needed.
- [x] green-frontend-code-block — implemented `codeBlock` as a Tiptap `Mark` (`codeBlockMark.ts`), same resolution as blockquote for the `inline*`-only schema, but `renderHTML` returns a nested `DOMOutputSpec` (`['pre', attrs, ['code', 0]]`) — verified empirically before locking in (ran the test, observed exact `<pre><code>hello world</code></pre>` output, no correction needed). `toggleCodeBlock` mirrors `toggleBlockquote`'s exact capture-cursor → expand-to-line → toggleMark → collapse-back pattern, proactively closing the selection-restore gap review passes flagged on the red commit (learned from blockquote's 3-round history — no separate corrective round needed here). `StarterKit.codeBlock: false` disables the built-in block node. Full suite: 62/62 passed, no regressions.
- [~] red-frontend-parseHTML — confirmed defect (agent-review, independently reproduced): `codeBlockMark.ts`'s `parseHTML: () => [{ tag: 'pre' }]` does not actually match — loading a document containing `<pre><code>hello world</code></pre>` (e.g. reopening a previously-saved document) produces `<code>hello world</code>` — the `<pre>` wrapper is silently dropped and StarterKit's still-enabled inline `code` mark claims the inner `<code>` tag instead. This downgrades a saved code block to inline code on reload — real formatting corruption on the load path, not just a live-editing quirk. Attempted fix (raising parse-rule `priority`) did not resolve it; needs deeper investigation (likely ProseMirror's mark-parsing interaction with `<pre>`'s block-level DOM semantics inside an inline-only doc schema). Add failing test: mock `getDocument` with `<pre><code>...</code></pre>` content, load via `existingDocumentId`, assert the loaded `innerHTML` round-trips correctly (mirrors `ManualEditor.horizontalRule.parseHTML.test.tsx`'s pattern).
- [ ] green-frontend-parseHTML — fix `codeBlockMark.ts`'s parse rule so `<pre><code>` content round-trips back into the `codeBlock` mark instead of being claimed by the inline `code` mark.
- [S] red-frontend-api — no API call: formatting is client-side editor state only, no backend endpoint involved
- [S] green-frontend-api — same reason
- [ ] align-design
- [S] green-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [S] demo — same reason, no live backend to drive a visible Selenium run against

### Scenario 7.5: Undo and redo revert and reapply the last editor change, disabled when there is nothing to undo/redo
- [S] red-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [ ] red-frontend
- [ ] green-frontend
- [S] red-frontend-api — no API call: formatting is client-side editor state only, no backend endpoint involved
- [S] green-frontend-api — same reason
- [ ] align-design
- [S] green-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [S] demo — same reason, no live backend to drive a visible Selenium run against

### Scenario 7.6: Applying an H3 heading changes the content and highlights the active toolbar button
- [S] red-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [ ] red-frontend
- [ ] green-frontend
- [S] red-frontend-api — no API call: formatting is client-side editor state only, no backend endpoint involved
- [S] green-frontend-api — same reason
- [ ] align-design
- [S] green-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [S] demo — same reason, no live backend to drive a visible Selenium run against

### Scenario 7.7: Applying underline changes the content and highlights the active toolbar button
- [S] red-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [ ] red-frontend
- [ ] green-frontend
- [S] red-frontend-api — no API call: formatting is client-side editor state only, no backend endpoint involved
- [S] green-frontend-api — same reason
- [ ] align-design
- [S] green-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [S] demo — same reason, no live backend to drive a visible Selenium run against

### Scenario 7.8: Applying text alignment changes the content and highlights the active toolbar button
- [S] red-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [ ] red-frontend
- [ ] green-frontend
- [S] red-frontend-api — no API call: formatting is client-side editor state only, no backend endpoint involved
- [S] green-frontend-api — same reason
- [ ] align-design
- [S] green-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [S] demo — same reason, no live backend to drive a visible Selenium run against

### Scenario 7.9: Applying a link changes the content and highlights the active toolbar button
- [S] red-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [ ] design — /design-preview: minimal URL-input interaction (window.prompt MVP vs inline popover), see plan jazzy-stirring-key.md § scenario 9
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [S] green-selenium — backend unavailable on this branch (backend developed in parallel session/branch); no live app to drive Selenium against
- [S] demo — same reason, no live backend to drive a visible Selenium run against
