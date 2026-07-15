## green-frontend (2026-07-15)

**Quirk:** The inline save-error banner text claims "введённый текст сохранён локально в редакторе" (the entered text is saved locally), but no localStorage/sessionStorage/IndexedDB persistence exists anywhere in the manual-mode feature.
**Where:** `ManualEditor.tsx`'s `saveError` message (`SAVE_ERROR_MESSAGE` constant), mockup `06-editor-error.html:85`.
**Implication:** The claim is only true within the same in-memory render — a refresh, tab close, or navigation after a failed save loses the content the banner just told the user was safe. Flagged BLOCK by premortem but not fixed in this scenario (out of scope); a future scenario adding real persistence, or a copy change removing the false claim, should account for this.

## red-frontend-api (2026-07-15)

**Quirk:** `saveDocument`'s rejection is a plain `Error` carrying only a message string — no HTTP status code or error kind is attached.
**Where:** `frontend/src/features/generation/api/httpClient.ts`'s `request()`/`readErrorMessage()`, consumed by `documentApi.ts`'s `saveDocument`.
**Implication:** `ManualEditor`'s catch handler cannot distinguish a 409 version-conflict from a network failure or a 500 — any scenario needing conflict-specific UX (e.g. reload-and-merge prompts) will need `saveDocument` to propagate a status/kind first.

## green-frontend (2026-07-15)

**Decision:** An edit made while a save is in-flight, if that in-flight save then rejects, is dropped from the retry queue rather than auto-resent — `saveAgainRequested.current` is unconditionally cleared in the catch handler.
**Why:** Scenario 5.2 scoped auto-retry-on-error as a separate concern from the queue-on-success mechanism built in scenario 4.2; the user must click Save again after a failure.
**Where applied:** `ManualEditor.tsx`'s `performSave` catch handler (`saveAgainRequested.current = false`).
