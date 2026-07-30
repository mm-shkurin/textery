import { useRef, useState } from 'react'
import type { Editor } from '@tiptap/react'
import { serializeEditorHtml } from '../components/serializeEditorHtml'
import { MAX_AUTOSAVE_ATTEMPTS } from './autosaveRetryPolicy'
import { isAlreadySaved } from './autosaveDirtyGuard'
import { performWrite } from './autosaveWriteChain'
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
  // Resolves only after the save — including any queued re-save and any backoff retry — fully
  // completes, and REJECTS on terminal failure. ExportControl awaits this on a dirty export: a save
  // that resolved on failure would let a stale file ship. The Save button consumes it
  // fire-and-forget.
  save: () => Promise<void>
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

  // The promise of the currently in-flight save chain. A second save() call while one is running
  // returns THIS, so a caller awaiting it (ExportControl on a dirty export) waits for the real
  // persistence to settle rather than an already-resolved promise.
  const inFlightRef = useRef<Promise<void> | null>(null)

  // One attempt, its resolve handling, and the bounded retry ladder — see autosaveWriteChain.
  const performSave = (saveVersion: number): Promise<void> => {
    if (!documentId || !editor) return Promise.resolve()
    return performWrite(
      {
        documentId,
        editor,
        cycle,
        isSavingRef,
        saveAgainRequested,
        lastSavedContentRef,
        setIsSaving,
        setVersion,
        setSaveError,
      },
      saveVersion,
    )
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
    save: (): Promise<void> => {
      if (!documentId || !editor) return Promise.resolve()
      if (isSavingRef.current) {
        saveAgainRequested.current = true
        // The in-flight chain, not a resolved promise: the queued re-save is folded into it (its
        // resolve handler runs performSave again), so awaiting this waits for that too.
        return inFlightRef.current ?? Promise.resolve()
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
        return Promise.resolve()
      }
      const promise = performSave(version)
      inFlightRef.current = promise
      return promise
    },
  }
}
