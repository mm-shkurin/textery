// How an autosave cycle ENDS, and the timer that keeps it alive between attempts (H9.4). Extracted
// from useDocumentSave, which had grown past the 200-line limit holding this alongside the request
// flow. React-free by construction: the refs arrive as plain `{ current }` boxes and the two state
// setters as plain callbacks, so nothing here imports React — the same shape as autosaveRetryPolicy,
// autosaveDirtyGuard and saveFailureMessages.
import { backoffDelay } from './autosaveRetryPolicy'
import { describeSaveFailure } from './saveFailureMessages'

// Structurally what `useRef` hands back, without depending on React's ref type. Exported because
// autosaveAbandonment reads two of the very refs declared below (isSavingRef, retryTimerRef) and
// has to spell their shape too — a second copy of the alias is a second thing to keep in step.
export type MutableRef<T> = { current: T }

export interface SaveCycleRefs {
  // True for the whole cycle INCLUDING the backoff gap, so an edit landing mid-wait only queues.
  isSavingRef: MutableRef<boolean>
  saveAgainRequested: MutableRef<boolean>
  // A scheduled transient retry lives here so unmount can cancel it — an editor the user navigated
  // away from must not fire a write at an abandoned document on a backoff timer.
  retryTimerRef: MutableRef<ReturnType<typeof setTimeout> | null>
  // The content the server last confirmed while the editor still held it. A terminal failure clears
  // it back to null ("unknown, never suppress").
  lastSavedContentRef: MutableRef<string | null>
  setIsSaving: (isSaving: boolean) => void
  // "An attempt was rejected and another one is scheduled" — a strictly narrower fact than
  // isSaving, which is already true before the FIRST request is even sent. Owned here because the
  // two places it can change are the two exits and the retry gate, all of which live in this file.
  setRetryPending: (retryPending: boolean) => void
  setSaveError: (error: string | null) => void
  onSaved: () => void
}

export interface SaveCycle {
  settleClean: () => void
  settleFailed: (error: unknown) => void
  scheduleRetry: (attempt: number, fire: () => void) => void
}

export function createSaveCycle(refs: SaveCycleRefs): SaveCycle {
  // Shared by both exits: whichever way the cycle ends, the queue is dropped and the saving state is
  // left. Clearing the retry-pending flag belongs here for the same reason — BOTH exits end the
  // ladder, including the terminal one, where a flag cleared only in the retry callback would leave
  // «повторяем…» co-rendered with the «не сохранено» banner forever.
  const leaveSaving = () => {
    refs.saveAgainRequested.current = false
    refs.isSavingRef.current = false
    refs.setIsSaving(false)
    refs.setRetryPending(false)
  }

  return {
    // The end of an in-flight cycle with nothing left to write: drop the queue, leave the saving
    // state, and tell the caller the document is clean. `onSaved` is the SOLE writer of the clean
    // flag, so every exit that stops writing has to come through here — a bare return would strand
    // the badge, beforeunload and the Сохранить button in the dirty state with no path back.
    settleClean: () => {
      leaveSaving()
      refs.onSaved()
    },

    // Non-transient, or the bounded retry budget is spent: give up. Drop the queued flag so a stale
    // retry doesn't fire later, but keep the user's latest content in the editor untouched so they
    // can manually retry by clicking Save again.
    //
    // And forget what the guard remembered. Suppression now settles the document CLEAN, so the
    // memory may only outlive events that leave it true — a terminal failure is not one. A
    // VersionConflictError here has already survived saveDocument's own refetch-and-retry, i.e.
    // another writer holds the document and the remembered content is provably not on the server.
    // Even for a plain network failure the banner says "not saved", and suppressing a later revert
    // would flip the badge to «Сохранено» right above it. Forgetting makes the next boundary a real
    // attempt instead — which is also the retry that clears the banner.
    settleFailed: (error: unknown) => {
      leaveSaving()
      refs.setSaveError(describeSaveFailure(error))
      refs.lastSavedContentRef.current = null
    },

    // Re-fire on the capped backoff. The cycle stays "saving" across the gap (settle* is the only
    // thing that clears it), so `fire` is the sole writer and any edit in the gap only queues.
    scheduleRetry: (attempt: number, fire: () => void) => {
      // Only reachable from the catch, so by construction an attempt has ALREADY been rejected —
      // which is what makes this flag say something isSaving cannot.
      refs.setRetryPending(true)
      refs.retryTimerRef.current = setTimeout(() => {
        refs.retryTimerRef.current = null
        fire()
      }, backoffDelay(attempt))
    },
  }
}
