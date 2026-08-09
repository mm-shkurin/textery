# Story 19: AI chat editing of an existing document (SSE, revisions, rollback) — Frontend Progress

Bootstrapped from the test spec on 2026-08-08. Owns: Frontend Scenarios only. Backend,
Integration, Security, Load and Infrastructure scenarios live in `progress-backend.md` —
never edited from this session. Narrative, decisions and the Spec checklist live in
`progress.md`; `ProductSpecification/stories.md` is the cross-file rollup.

The UI test spec is split across three files (see the Decisions section of `progress.md`);
each file gets its own section below, and scenario numbers are unique within their file,
not across the story. 35 scenarios total (10 + 12 + 13).

Nothing is implemented yet: no AI-chat component, hook, API client or Selenium test exists
under `frontend/src` or `acceptance/tests/frontend`.

## Frontend Scenarios (02_UI_Tests.md)

### 0.1 A document that cannot be loaded blocks the chat panel with a way out
- [x] red-selenium — one test, three Statements assertions. Predicted and got
      `TimeoutException` in `_wait_for_visible` on `[data-testid='document-not-found']`.
      `/test-review` landed five fixes: the way-out link now asserts its `href` resolves to
      `{app_url}/documents` **and** that the link is a descendant of the blocker (caption-only
      would have passed a `<span>` or an `href="#"`); the chat-panel absence check moved to the
      prefix locator `[data-testid^='ai-chat']` because the exact `ai-chat-panel` testid exists
      nowhere and nothing forces scenario 1.1 to choose that name — the check was permanently
      vacuous; the `driver.get` justification was re-argued from the durable reason (a
      not-found document is unreachable by clicking your own documents list, by construction)
      rather than from a documents list that does not exist yet; and the skip reason now says
      the route itself is absent. Absence stays `find_elements`-based on purpose — a
      non-visibility check would pass a rendered-but-hidden editor.
      **Work unit closed 2026-08-09:** `/refactor` and both review passes ran over `3ec4798a`.
      Refactor migrated the two duplicated `_assert_absent` idioms
      (`manual_editor_statements.py:74`, `mode_modal_statements.py:41`) onto the base class and
      dropped a dead local in `chat_workspace_statements.py:72` that was failing ruff. Selenium
      did not execute — the stack is down; evidence is collection (35 collected, 0 errors),
      ruff clean, and import resolution.
      **Follow-ups surfaced (non-gating, act on them in `red-frontend`/`green-frontend`):**
      (a) `MANUAL_EDITOR = [data-testid='manual-editor']` is vacuous the same way the chat-panel
      locator was — that testid belongs to the Story 5/18 manual editor, and nothing forces the
      new `/documents/:id` editor to reuse it; widen it or pin it once green names its root.
      (b) In `assert_documents_list_link_is_offered` the descendant check searches inside the
      blocker while the text/href checks search the whole document, so a chrome link and a
      blocker `href="#"` can satisfy them jointly — assert a single match, or run text/href
      against the element found under `blocker`.
      (c) The route is only ever opened with a random UUID, so nothing proves the blocker is
      *conditional*: green can render it unconditionally and stay green. Owe a counter-case
      (own document opens the editor, blocker absent) and a foreign-document case.
      (d) The class is `@pytest.mark.skip` with no gate that fails on a lingering skip — verify
      the un-skip actually happened at `green-selenium`.
      (e) Pre-existing, out of unit: 10 `unused import: pytest` ruff errors across 9 frontend
      and 1 backend test files; `LOADING_SKELETON`/`SOON_BADGE` use class-based selectors,
      which `frontend-rules.md:45` forbids.
      **Harness quirk:** `pytest -m frontend` defaults `app_url` to port 5173 while
      `FRONTEND_PORT=80` lives in `infra/.env` — export it first (`set -a; . ../infra/.env`),
      or the run dies with `ERR_CONNECTION_REFUSED`, which looks nothing like a red test.
- [x] red-frontend — two cases, one branch, in
      `frontend/src/features/aiChat/components/__tests__/DocumentEditorPage.notFound.test.tsx`.
      Predicted and got `TestingLibraryElementError: Unable to find an element by:
      [data-testid="document-not-found"]` on the failure case and `AssertionError: expected null
      not to be null` on the success case. The success case is what closes follow-up (c): an
      unconditional blocker now fails. `/test-review` landed six fixes — the biggest is that
      `manual-editor` had no positive counterpart anywhere for this route, so the absence check
      was vacuous exactly as follow-up (a) said; the success case now *requires* that testid to
      render, proving the same constant live in one branch and absent in the other. The chat
      locators are deliberately asymmetric: absence uses the prefix `[data-testid^='ai-chat']`
      (un-slippable), presence uses the exact `ai-chat-panel` — `not.toBeNull()` on a prefix is
      satisfied by any incidental wrapper. Both load calls pinned with
      `toHaveBeenCalledExactlyOnceWith` (an unpinned count passed a component that refetches on
      every render), and the way-out link asserts `tagName === 'A'` before its href (a
      `<span href>` navigates nowhere). `version: 3` is left unasserted on purpose — no UI
      scenario shows it; it travels with edit submissions in scenarios 3.x.
      **Green-frontend scope is three things, not one:** the `/documents/:documentId` route in
      `app/App.tsx`, the blocker, and a `/documents` list for the way-out link to target.
      **Harness note:** `frontend/node_modules` was absent; `npm ci` (273 packages, ~2 min) is
      needed before the suite runs — an empty `node_modules` looks like a broken config.
      `/refactor` found NO ACTION (141/7/28 lines, oxlint and tsc clean); no refactor commit.
      It flagged two deferrals for `red-frontend-api`: `loadEditorDocument`/`EditorDocument`
      duplicates `getDocument`/`GetDocumentResult` in `generation/api/documentApi.ts` (same
      shape, same endpoint) — do not land a second document loader without deciding that; and
      `DocumentNotFoundError` belongs beside `VersionConflictError`/`SessionExpiredError` in
      `shared/api/send.ts` once something actually throws it.
      **Review-pass follow-ups for `green-frontend` (verified where noted):**
      (f) **The coverage gate is red on `f1e3f306` — confirmed, `npm run test:coverage` exits 1.**
      Both stubs sit at 0% statements against a 60% per-file floor. This is inherent to a RED
      phase that lands stubs behind a skipped test; green closes it by un-skipping. Do not
      lower the floor or add an exclude. Any CI job running `test:coverage` fails here, and the
      failure looks like a coverage problem rather than an in-flight red phase.
      (g) The success case asserts a live `ai-chat-panel`, which is scenario 1.1's component —
      so green's scope is *four* things, not the three listed above. An empty placeholder div
      named `ai-chat-panel` would satisfy it and reintroduce exactly the incidental-wrapper pass
      the asymmetric locators were chosen to prevent. Decide this before green starts.
      (h) Every rejection currently maps to the blocker. The minimal code passing both cases is
      `try { … } catch { setNotFound(true) }`, which shows "Документ не найден" on a 500, on a
      401, on a dropped connection — and invites the user to re-create a document that exists.
      Owe a case rejecting with a generic `Error` and asserting the blocker is **absent**.
      (i) Both suites assert the way-out link's `href`, neither ever clicks it. `App.tsx:16`
      routes `/*` to `DocumentGenerationFlow`, so `/documents` resolves today and green can ship
      without ever building the list. Owe an App-level case that clicks the link and asserts the
      documents list — not the generation flow — renders.
      (j) `/documents/:documentId` is currently swallowed by that same `/*` catch-all, which
      renders `ManualEditor` — already carrying `data-testid="manual-editor"`, the testid this
      test reuses for the new page root. Sibling routes never mount together so `getByTestId`
      stays unambiguous, but `src/__tests__/App.test.tsx:131,146,150` assert on that testid at
      app level; composing the two editors would break them.
      (k) `toHaveBeenCalledExactlyOnceWith` is proved outside StrictMode while `main.tsx` wraps
      `App` in it, so a naive `useEffect` fetch passes here and double-invokes in dev. The repo
      already has `generation/hooks/__tests__/useDocumentInit.strictMode.test.tsx` for this.
      (l) Nothing fails on a permanently-skipped spec. Green's verification must report these
      two cases as *passed*, not merely "suite green".
- [~] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 0.2 An account over its daily quota cannot type an instruction
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 1.1 The editor and chat panel render side by side with an empty history
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 1.2 An existing conversation is restored when the document is reopened
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 1.3 The chat history and the revisions panel each show their own load failure
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 2.1 Selecting text attaches the excerpt to the next instruction
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 3.1 Sending an instruction freezes the editor and offers cancellation
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 3.2 One gesture produces at most one instruction
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 3.3 A dirty buffer is not silently discarded when an instruction is sent
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 3.4 Leaving with unsaved content is guarded
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

## Frontend Scenarios (02_UI_Tests_Streaming.md)

### 4.1 Streamed text appears progressively as plain text
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 4.2 A dropped stream shows a reconnecting state distinct from a stalled one
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.1 A completed edit unfreezes the editor and shows the applied result
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.2 A failed edit reverts the buffer and offers a retry
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.3 Cancelling reverts without presenting a failure
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.4 The client timeout releases the editor rather than freezing it forever
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.5 An unrecognised terminal outcome is treated as a failure, not a success
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 6.1 Revisions are listed with their number, time and source
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 6.2 Restoring asks for confirmation and explains that nothing is destroyed
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 6.3 A superseded response never overwrites the current view
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 7.1 The revisions panel can be opened and closed from the editor
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 7.2 The not-found blocker's link returns to the documents list
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

## Frontend Scenarios (02_UI_Tests_Guards.md)

### 8.1 Selection offsets are sent as code points, not as editor indices
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.2 A retry after a lost response does not create a second edit
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.3 An edited retry carries a new key and is actually executed
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.4 The client timeout releases the server edit, not only the editor
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.5 A stale or post-terminal event is ignored
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.6 An unrecognised non-terminal event does not break the stream
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.7 A failed re-fetch after completion never leaves unsanitised text on screen
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.8 The document load has a loading state and a distinct failure state
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.9 A failed restore leaves the pre-restore content in place
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.10 Restoring cannot be double-submitted
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.11 A session expiring with unsaved content does not discard it
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.12 Revision times are shown in the intended day
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 8.13 Stream reconnection backs off rather than retrying in a tight loop
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo
