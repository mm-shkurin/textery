import { useEffect, useRef } from 'react'
import type { MutableRef } from '../utils/autosaveSaveCycle'

// What the editor leaves behind when it dies with a write still unfinished (H9.4). Extracted from
// useDocumentSave — which is at the 200-line limit — rather than grown inline.
//
// The ref shape comes from autosaveSaveCycle, which declares the two refs read below as part of
// SaveCycleRefs: this file describes the same boxes, so it names their type once, over there.

// The app has no reporting backend, so console.error is the whole of its diagnostics.
//
// The autosave fixture holds an independently-written copy of this exact string, and that copy is
// deliberate rather than an oversight: it is the tripwire. Nothing imports one from the other, so
// rewording the message here does not quietly follow through to the assertions — it fails every
// abandonment suite, which is the point at which the wording gets re-decided on purpose. Importing
// the fixture's expectation from this constant would make those assertions tautological.
export const ABANDONED_SAVE_LOG = 'Pending document save abandoned before it completed'

// Cancel a pending backoff retry on unmount — an editor the user navigated away from must not fire a
// write at an abandoned document on a timer — and record that the write was dropped.
//
// The record is keyed on "there is an unfinished write", NOT on "a retry timer object exists". That
// covers TWO windows, and both of them are ordinary:
//
//   - a write already started — `isSavingRef`, true for the whole cycle including the backoff gaps.
//     The ~7-second ladder is mostly NOT gaps: four of its sub-windows are in-flight requests where
//     retryTimerRef is null and the write is just as abandoned.
//   - a write DECIDED ON but not yet started — the debounce gap, the only one a user reaches without
//     a 5xx first. isSavingRef is still false there, and useAutosave's own []-scoped cleanup drops
//     the pending timer in silence.
//
// The second window is tracked by the boolean returned below rather than by reading useAutosave's
// timer ref: that ref is NULLED by useAutosave's own unmount cleanup, so reading it here would make
// the record depend on the relative order of two []-scoped effects' cleanups. This flag is set when
// an edit arms the debounce and cleared only when `save()` actually runs — unmount never touches it.
//
// And the inverse matters as much as either window: a fully-settled document, or an untouched one,
// backed out of normally must write nothing — otherwise the one record that means something drowns in
// a record written on every ordinary exit. Note "untouched" is NOT the same as "clean": a freshly
// created document reads dirty with nothing typed, which is why the key is pending work, not the
// dirty flag.
//
// Deliberately []-scoped and reading the refs directly: anything render-scoped here would re-run the
// cleanup every render and cancel a live retry.
//
// Returns the pending-edit flag so the debounce scheduler can arm it. Owned here, beside the cleanup
// that reads it, rather than in useDocumentSave — which is at the file-size limit.
// `hasUnwrittenContent` is the third and last condition, and it is what keeps the record about the
// SERVER's copy rather than about a flag. An edit reverted to the saved bytes inside the debounce
// gap — Ctrl+Z, backspacing the one new character, bold-then-unbold — re-arms the deadline through
// noteEdit, so the flag is honestly true while there is provably nothing to write: had the timer
// been allowed to fire, `save()` would have taken the already-saved branch and sent nothing.
// Reporting that as a lost write is how the one record that means something drowns.
//
// It is read through a callback rather than compared here because what "unwritten" means (serialize
// the editor, compare against the last confirmed content) belongs to the save hook, and this file
// deliberately knows nothing about editors.
export function useAbandonedSaveRecord(
  isSavingRef: MutableRef<boolean>,
  retryTimerRef: MutableRef<ReturnType<typeof setTimeout> | null>,
  hasUnwrittenContent: () => boolean,
): MutableRef<boolean> {
  const hasPendingEditRef = useRef(false)
  // Read through a ref for the same reason `save` is in useAutosave: the cleanup below is []-scoped
  // and closes over the FIRST render's callback, which would compare against a stale
  // lastSavedContent — the value from before every save the editor went on to make.
  const unwrittenRef = useRef(hasUnwrittenContent)
  unwrittenRef.current = hasUnwrittenContent

  useEffect(
    () => () => {
      if (retryTimerRef.current !== null) clearTimeout(retryTimerRef.current)
      const unfinished = isSavingRef.current || hasPendingEditRef.current
      if (unfinished && unwrittenRef.current()) console.error(ABANDONED_SAVE_LOG)
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  return hasPendingEditRef
}
