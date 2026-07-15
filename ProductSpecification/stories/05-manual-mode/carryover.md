## Quirk: flex containers break Selenium text assertions

**Quirk:** `display: flex` on a container whose children are meant to read as one continuous line makes the browser's innerText/Selenium `.text` insert a newline between every flex item, even though visually they render side by side.
**Where:** Was in `ManualEditor.css` (`.me-breadcrumb-chips`, `.me-breadcrumb-chip`); fixed by switching to `inline-block` + `white-space: nowrap` with `vertical-align`/`margin` for icon alignment instead of `gap`.
**Implication:** Any future breadcrumb-style or inline-badge component whose text is asserted via Selenium `.text` must avoid `flex`/`inline-flex` on the text-bearing container — use inline-block/vertical-align instead, or normalize whitespace in the Statements assertion.
**From:** scenario 1.2 (manual-editor-opens)

## Quirk: save-error banner falsely claims local persistence

**Quirk:** The inline save-error banner text claims "введённый текст сохранён локально в редакторе" (entered text is saved locally), but no localStorage/sessionStorage/IndexedDB persistence exists anywhere in the manual-mode feature — content only survives in in-memory Tiptap/React state.
**Where:** `ManualEditor.tsx`'s `SAVE_ERROR_MESSAGE` constant, mockup `06-editor-error.html:85`.
**Implication:** A refresh, tab close, or navigation after a failed save loses content the banner claims is safe. Scenario 6.2 (reopening a saved document) and any future persistence/offline work should treat this as an open, unresolved BLOCK-severity gap rather than a resolved one.
**From:** scenario 5.2 (failed-save-inline-error)

## Quirk: save rejections carry no distinguishable status/kind

**Quirk:** `saveDocument`'s rejection is a plain `Error` with only a message string — no HTTP status code or error kind is attached.
**Where:** `frontend/src/features/generation/api/httpClient.ts`'s `request()`/`readErrorMessage()`, consumed by `documentApi.ts`'s `saveDocument`.
**Implication:** `ManualEditor` cannot distinguish a 409 version-conflict from a network failure or a 500 today. Any scenario needing conflict-specific UX (reload-and-merge prompts, distinguishing retryable vs. fatal errors) must first extend `saveDocument`/`request()` to propagate a status/kind.
**From:** scenario 5.2 (failed-save-inline-error)
