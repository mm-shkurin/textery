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

## green-frontend (2026-07-27)

**Decision:** `lastSavedContentRef` records the persisted content only when the editor still holds what was sent — otherwise `null`, meaning "unknown, never suppress".
**Why:** Keying on `sent` stops matching after any sanitizing save (idle PUT loop); keying on `result.content` unconditionally records text the editor never held when a mid-flight edit blocked adoption (silent data loss).
**Where applied:** `frontend/src/features/generation/hooks/autosaveDirtyGuard.ts` (`savedContentAfterResolve`), called from `performSave`'s `.then` after the adoption decision.

## green-frontend (2026-07-27)

**Quirk:** Adopting a sanitized `result.content` via `setContent` emits an update, which sends the server's own form straight back as one echo PUT through the queued `saveAgainRequested` path.
**Where:** `ManualEditor.tsx:81-83` — the E3.1 comment claiming `setContent` does not re-dirty is not accurate for the adoption path.
**Implication:** The dirty guard sits in `save()` and cannot see that echo; any future write-amplification count must expect one extra PUT per sanitizing save.

## green-frontend (2026-07-27)

**Surprise:** Suppressing the redundant write also suppressed the only path that settles the clean state — the guard's bare early return skips `performSave`, hence `onSaved()`, so a reverted edit left the document stuck dirty with a dead Save button.
**Why:** `onSaved()` is the sole writer of `setHasUnsavedChanges(false)` while `noteEdit` fires `onDirty()` on every update, including the one restoring the saved content.
**Impact:** All six guard tests entered the guard from an already-clean state, so the suite was green over a user-visible regression; any new suppression branch must be exercised from a dirty state.

## red-frontend (2026-07-27)

**Quirk:** A `beforeunload` assertion of `preventDefault`-not-fired proves nothing on its own — the listener is registered behind `if (!hasUnsavedChanges) return`, so a regression that never arms it satisfies the assertion.
**Where:** `ManualEditor.tsx:127-138`; helper `dispatchBeforeUnload` in `ManualEditor.saveStatus.testSupport.tsx`.
**Implication:** Every stand-down assertion needs a preceding armed assertion (`toBe(true)`) at a provably-dirty moment, or it passes vacuously.
