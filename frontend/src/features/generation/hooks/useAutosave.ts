import { useEffect, useRef } from 'react'

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
export function useAutosave(save: () => void): () => void {
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
    timerRef.current = setTimeout(() => {
      timerRef.current = null
      saveRef.current()
    }, AUTOSAVE_DEBOUNCE_MS)
  }
}
