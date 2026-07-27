// The autosave dirty guard (H9.4): does the editor still hold exactly the content the server last
// confirmed? Pure and React-free — the save state machine in useDocumentSave consumes it, the same
// way it consumes autosaveRetryPolicy.
//
// Why it exists: an edit landing during an in-flight autosave does TWO things — it queues a
// mid-flight re-save AND arms a fresh debounce timer. The queued re-save persists the latest content
// and marks the document clean, but the timer it armed is never cleared, so crossing that deadline
// fires a redundant PUT over content that is already saved (version churn / write amplification).
//
// The guard is deliberately NOT a timer-cancel inside noteEdit: cancelling at arm time would also
// throw away the debounce in the case where the queued re-save FAILS — and there the debounce is the
// only thing left that will retry. Suppressing at FIRE time, on the content, keeps that retry alive.

// What the guard may remember as "saved" once a save resolves.
//
// `persistedContent` is the server's own copy (already sanitized: it strips <script> with its
// contents and normalises void tags), and `currentContent` is what the editor holds AFTER the
// resolve handler has decided whether to adopt it. Two keyings are both wrong and both silent:
//
//   - remembering what we SENT: after any sanitizing save the editor holds the adopted server form,
//     which never equals the sent form again, so the guard never bites — the idle PUT loop survives.
//   - remembering the server's copy UNCONDITIONALLY: when adoption was skipped because the user
//     typed mid-flight, the editor holds text the server has never seen, and recording the server's
//     copy would let a later boundary be suppressed over genuinely unsaved words (data loss, with
//     beforeunload and the badge disagreeing about it).
//
// So it is remembered only when the two agree — otherwise `null`, meaning "unknown, never suppress".
export function savedContentAfterResolve(
  currentContent: string,
  persistedContent: string,
): string | null {
  return currentContent === persistedContent ? persistedContent : null
}

// Whether a save may be skipped. `null` (no confirmed save yet, or a save that resolved while the
// editor held something else) always answers false: the guard suppresses only over content it has
// positively watched the server confirm, never by default.
export function isAlreadySaved(currentContent: string, lastSavedContent: string | null): boolean {
  return lastSavedContent !== null && currentContent === lastSavedContent
}
