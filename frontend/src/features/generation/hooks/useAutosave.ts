import { useEffect, useRef } from 'react'
import type { MutableRef } from '../utils/autosaveSaveCycle'

// How long typing must be quiet before an edit autosaves. Landing a save exactly on this boundary
// (not "somewhere after it") is what the E3.1 test pins, so the constant is the single source both
// the hook and the test agree on.
export const AUTOSAVE_DEBOUNCE_MS = 1000

// Debounced autosave, extracted to its own file so neither useDocumentSave nor ManualEditor crosses
// the 200-line limit. It owns NO save machinery of its own — it only decides WHEN to call the
// existing `save()`. Every edit reschedules: the prior timer is cleared so a burst of keystrokes
// collapses to ONE save fired once typing stops, never one save per keystroke.
//
// The timer id lives in a ref (stable across renders) and `save` is read through a ref so a
// rescheduled edit always fires the latest closure without re-arming the effect. The cleanup clears
// a pending timer on unmount — an editor the user has navigated away from must not fire a write at
// an abandoned document (and trigger a state update on an unmounted component).
//
// `hasPendingEdit` is the abandonment record's view of this hook (H9.4): set the moment an edit arms
// the debounce, cleared only when the timer actually fires `save()`. Deliberately NOT cleared by the
// unmount cleanup below — unmounting inside the gap is precisely the case the record exists for, and
// the flag is what tells it apart from an untouched document. It is a separate boolean rather than
// `timerRef !== null` because `clearPending` nulls that ref on unmount, which would make the record
// depend on the order two []-scoped effect cleanups happen to run in.
export function useAutosave(
  save: () => Promise<void>,
  hasPendingEdit: MutableRef<boolean>,
): () => void {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const saveRef = useRef(save)
  saveRef.current = save

  // Cancel any pending autosave. Shared by unmount cleanup (drop an abandoned write) and by every
  // reschedule (a fresh edit supersedes the prior deadline). Nulling after clearTimeout keeps the
  // "is a save pending?" check on timerRef honest between the two call sites.
  const clearPending = () => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }

  useEffect(() => clearPending, [])

  return () => {
    clearPending()
    hasPendingEdit.current = true
    timerRef.current = setTimeout(() => {
      timerRef.current = null
      // The flag is NOT cleared here. A fired timer means the save was HANDED OVER, not that it
      // happened: `save()` returns at once when there is no document to write to, and clearing on
      // the handover made that case — the one where the work is most thoroughly lost — read as an
      // untouched editor at unmount. `save()` clears it once it has something that will write the
      // edit, or has established there is nothing left to write.
      // `save()` REJECTS on terminal failure so an awaiting caller (ExportControl on a dirty
      // export) can skip shipping a stale file. The debounce fires it unattended, so the rejection
      // has to be swallowed HERE or it surfaces as an unhandled rejection — the banner and the
      // dirty flag were already set by settleFailed before the rethrow, so nothing is lost.
      void saveRef.current().catch(() => {})
    }, AUTOSAVE_DEBOUNCE_MS)
  }
}
