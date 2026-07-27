# Scenario H9.4 — Rapid typing coalesces to a bounded save rate

## red-frontend (2026-07-27)

**Expected:** `AssertionError: expected "saveDocument" to be called 2 times, but got 3 times`
**Actual:** `AssertionError: expected "vi.fn()" to be called 2 times, but got 3 times`
**Why:** `vi.mock('../../api/documentApi')` auto-mocks the module into unnamed spies, so Vitest has no export name to print and falls back to `vi.fn()`.
**Resolution:** Predicted the literal `vi.fn()` text instead of the export name and re-ran; the corrected prediction reproduced exactly.

## red-frontend (2026-07-27)

**Decision:** The dirty-guard that suppresses the redundant trailing PUT goes in `useDocumentSave.save()` (or a `lastSavedContent` ref compared against `serializeEditorHtml(editor)`), not a timer-cancel inside `noteEdit`.
**Why:** The debounce timer is legitimately armed when the mid-flight edit lands and only becomes redundant once the queued re-save happens to persist that same content — cancelling at arm time would remove the only retry left when that queued re-save FAILS.
**Where applied:** `frontend/src/features/generation/hooks/useDocumentSave.ts`
