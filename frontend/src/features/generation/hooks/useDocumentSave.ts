import { useRef, useState } from 'react'
import type { Editor } from '@tiptap/react'
import { saveDocument } from '../api/documentApi'
import { serializeEditorHtml } from '../components/serializeEditorHtml'
import {
  MAX_AUTOSAVE_ATTEMPTS,
  isTransientFailure,
  mayHaveLandedServerSide,
} from './autosaveRetryPolicy'
import {
  isAlreadySaved,
  savedContentAfterResolve,
  shouldAdoptPersistedContent,
} from './autosaveDirtyGuard'
import { createSaveCycle } from './autosaveSaveCycle'
import type { MutableRef } from './autosaveSaveCycle'
import { useAbandonedSaveRecord } from './autosaveAbandonment'
import { CONFLICT_ERROR_MESSAGE, SAVE_ERROR_MESSAGE } from './saveFailureMessages'

// Re-exported so callers (and the retry-backoff / failure-copy tests) keep importing the attempt
// ceiling and the failure copy from the save hook — one definition lives in autosaveRetryPolicy and
// saveFailureMessages respectively, these are just their public surface here.
export { MAX_AUTOSAVE_ATTEMPTS }
export { SAVE_ERROR_MESSAGE, CONFLICT_ERROR_MESSAGE }

interface UseDocumentSaveParams {
  documentId: string | null
  editor: Editor | null
  onSaved: () => void
  onDirty: () => void
}

export interface DocumentSave {
  // "An edit has been decided on but not sent yet", written by the debounce scheduler and read by the
  // unmount abandonment record. Owned by useAbandonedSaveRecord, passed through here because the
  // scheduler is wired up after this hook — see autosaveAbandonment and useAutosave.
  hasPendingEditRef: MutableRef<boolean>
  isSaving: boolean
  // An attempt has been rejected and the capped backoff has another one scheduled. Strictly
  // narrower than isSaving, which is true from before the first request is sent.
  isRetryPending: boolean
  saveError: string | null
  setVersion: (version: number) => void
  // Call on every edit: an edit landing mid-flight has to queue a re-save.
  noteEdit: () => void
  save: () => void
}

// The save state machine, extracted from ManualEditor — which was over the 200-line limit and
// held this, the editor construction, and the layout all at once.
//
// It is a state machine written as callbacks, and the four pieces of state are not redundant:
// `isSavingRef`/`saveAgainRequested` are refs because the in-flight resolve handler reads them
// from a closure minted before the click that changed them, and a state read there would be
// stale. `isSaving` is the same fact as `isSavingRef` in a form that re-renders the toolbar.
export function useDocumentSave({
  documentId,
  editor,
  onSaved,
  onDirty,
}: UseDocumentSaveParams): DocumentSave {
  // Every document starts at version 1; useDocumentInit calls setVersion with the server's value
  // for an existing document, and each save's resolve advances it.
  const [version, setVersion] = useState(1)
  const [isSaving, setIsSaving] = useState(false)
  const [isRetryPending, setIsRetryPending] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const isSavingRef = useRef(false)
  const saveAgainRequested = useRef(false)
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastSavedContentRef = useRef<string | null>(null)
  // How a cycle ends and how the backoff timer is kept — see autosaveSaveCycle.
  const cycle = createSaveCycle({
    isSavingRef,
    saveAgainRequested,
    retryTimerRef,
    lastSavedContentRef,
    setIsSaving,
    setRetryPending: setIsRetryPending,
    setSaveError,
    onSaved,
  })
  // Cancels a pending backoff retry on unmount and records a write abandoned by it — see
  // autosaveAbandonment.
  const hasPendingEditRef = useAbandonedSaveRecord(isSavingRef, retryTimerRef)

  // `attempt` is 1 for the initial save and increments on each transient retry. `isSavingRef` stays
  // true across the backoff wait so an edit or Сохранить click landing in the gap only QUEUES
  // (saveAgainRequested) rather than launching a competing save — and the retry re-serializes the
  // editor's CURRENT content, so a keystroke typed during the wait is re-sent, never silently lost.
  const performSave = (saveVersion: number, attempt = 1) => {
    if (!documentId || !editor) return
    isSavingRef.current = true
    setIsSaving(true)
    saveAgainRequested.current = false
    // Captured before the round trip: the response's content is the SANITIZED persisted form,
    // and telling whether to adopt it requires knowing what we actually sent.
    const sent = serializeEditorHtml(editor)
    saveDocument(documentId, sent, saveVersion)
      .then((result) => {
        // Whether to take the server's sanitized form into the editor — rules and rationale live
        // beside the guard that reads the result (autosaveDirtyGuard).
        if (shouldAdoptPersistedContent(sent, serializeEditorHtml(editor), result.content)) {
          editor.commands.setContent(result.content)
        }
        // Read AFTER the adoption decision above: what the editor holds now is what the guard may
        // call saved, and only if the server's copy agrees with it (see autosaveDirtyGuard).
        lastSavedContentRef.current = savedContentAfterResolve(
          serializeEditorHtml(editor),
          result.content,
        )
        setVersion(result.version)
        setSaveError(null)
        if (saveAgainRequested.current) {
          saveAgainRequested.current = false
          performSave(result.version)
        } else {
          cycle.settleClean()
        }
      })
      .catch((error) => {
        // The banner tells the user WHAT happened; this is the only place the underlying error
        // object survives at all. There is no reporting sink, so the console is the whole of the
        // diagnostics — deleting it would leave a failed save with no trace anywhere.
        console.error('Failed to save document', error)
        // A transient failure with attempts left re-fires itself on a capped backoff — no fresh
        // edit and no click needed. Stay in the saving state (isSavingRef true, no banner yet) so
        // the retry is the sole writer and any edit in the gap only queues. The retry re-serializes
        // current content at fire time (below), so a queued edit's LATEST text is what gets sent.
        if (isTransientFailure(error) && attempt < MAX_AUTOSAVE_ATTEMPTS) {
          // Same principle settleFailed already applies, reaching the retry gate below: a failure
          // that may have LANDED leaves the server's content unknown, so the guard's memory of what
          // the server holds cannot outlive it — otherwise a revert inside the backoff window is
          // suppressed against a memory the failure itself put in doubt, and the editor and the
          // server silently diverge under a «Сохранено» badge. A definite refusal (503) keeps the
          // memory: it is still provably true, and suppressing a redundant re-PUT there is correct.
          if (mayHaveLandedServerSide(error)) lastSavedContentRef.current = null
          cycle.scheduleRetry(attempt, () => {
            // The backoff window is the one place save() cannot apply the guard: isSavingRef is
            // still true, so an edit landing here takes the queue branch and returns before the
            // check. Undo an edit in that gap and the queue now points at content the server
            // already has — firing it would write it again AND chain a second write off the
            // resolve. Fire time is when the question is finally answerable, so ask it here.
            if (isAlreadySaved(serializeEditorHtml(editor), lastSavedContentRef.current)) {
              cycle.settleClean()
              return
            }
            performSave(saveVersion, attempt + 1)
          })
          return
        }
        cycle.settleFailed(error)
      })
  }

  return {
    hasPendingEditRef,
    isSaving,
    isRetryPending,
    saveError,
    setVersion,
    // An edit that lands while a save is already in flight must queue a re-save even without an
    // explicit second click: otherwise the in-flight save's resolve handler has no signal that
    // newer, unsent content exists, and would wrongly mark the document clean.
    noteEdit: () => {
      onDirty()
      if (isSavingRef.current) {
        saveAgainRequested.current = true
      }
    },
    save: () => {
      if (!documentId || !editor) return
      if (isSavingRef.current) {
        saveAgainRequested.current = true
        return
      }
      // Nothing to write: the editor holds exactly what the server confirmed. This is what makes the
      // stale debounce timer left armed by a mid-flight edit inert. Checked only when NO save is in
      // flight — mid-flight the ref describes the PREVIOUS save, and skipping the queue there could
      // strand the editor holding older content than the request already on the wire.
      // Suppressing the write is only half the answer: an edit reverted to the saved content (undo,
      // backspacing the one new character, bold-then-unbold) still ran onDirty on the way back, so
      // returning bare here left hasUnsavedChanges true with nothing able to clear it — badge stuck
      // dirty, beforeunload armed forever, and Сохранить a dead button routing into this same
      // branch. The document genuinely IS clean, so say so.
      if (isAlreadySaved(serializeEditorHtml(editor), lastSavedContentRef.current)) {
        onSaved()
        return
      }
      performSave(version)
    },
  }
}
