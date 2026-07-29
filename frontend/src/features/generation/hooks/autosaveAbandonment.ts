import { useEffect } from 'react'
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
// The record is keyed on `isSavingRef`, i.e. "there is an unfinished write", NOT on "a retry timer
// object exists". The ~7-second backoff ladder is mostly NOT gaps: four of its sub-windows are
// in-flight requests where retryTimerRef is null and the write is just as abandoned. And the inverse
// matters as much: a fully-settled document backed out of normally must write nothing, or the one
// record that means something drowns in a record written on every ordinary exit.
//
// Deliberately []-scoped and reading the refs directly: anything render-scoped here would re-run the
// cleanup every render and cancel a live retry.
export function useAbandonedSaveRecord(
  isSavingRef: MutableRef<boolean>,
  retryTimerRef: MutableRef<ReturnType<typeof setTimeout> | null>,
) {
  useEffect(
    () => () => {
      if (retryTimerRef.current !== null) clearTimeout(retryTimerRef.current)
      if (isSavingRef.current) console.error(ABANDONED_SAVE_LOG)
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )
}
