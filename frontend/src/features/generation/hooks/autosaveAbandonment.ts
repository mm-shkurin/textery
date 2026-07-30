import { useEffect, useRef } from 'react'
import type { MutableRef } from './autosaveSaveCycle'

// What the editor leaves behind when it dies with a write still unfinished (H9.4). Extracted from
// useDocumentSave — which is at the 200-line limit — rather than grown inline.
//
// The ref shape comes from autosaveSaveCycle, which declares the two refs read below as part of
// SaveCycleRefs: this file describes the same boxes, so it names their type once, over there.

// The app has no reporting backend, so console.error is the whole of its diagnostics. Duplicated
// nowhere: the tests import their own copy of this string from the autosave fixture, and the two are
// pinned to each other by the suites that assert it.
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
export function useAbandonedSaveRecord(
  isSavingRef: MutableRef<boolean>,
  retryTimerRef: MutableRef<ReturnType<typeof setTimeout> | null>,
): MutableRef<boolean> {
  const hasPendingEditRef = useRef(false)

  useEffect(
    () => () => {
      if (retryTimerRef.current !== null) clearTimeout(retryTimerRef.current)
      if (isSavingRef.current || hasPendingEditRef.current) console.error(ABANDONED_SAVE_LOG)
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  return hasPendingEditRef
}
