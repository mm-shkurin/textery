// The write chain of an autosave: one attempt, what its resolve adopts, and the bounded transient
// retry ladder underneath it. Extracted from useDocumentSave, which crossed the 200-line limit
// once the chain had to return a promise as well as drive the cycle. React-free like its siblings
// (autosaveSaveCycle, autosaveRetryPolicy, autosaveDirtyGuard): refs arrive as plain `{ current }`
// boxes, so nothing here imports React.
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
import type { MutableRef, SaveCycle } from './autosaveSaveCycle'

export interface WriteChainDeps {
  documentId: string
  editor: Editor
  cycle: SaveCycle
  isSavingRef: MutableRef<boolean>
  saveAgainRequested: MutableRef<boolean>
  lastSavedContentRef: MutableRef<string | null>
  setIsSaving: (isSaving: boolean) => void
  setVersion: (version: number) => void
  setSaveError: (error: string | null) => void
}

// Returns a promise that settles only when the WHOLE chain does — including a queued re-save and
// every backoff retry — and REJECTS on terminal failure. ExportControl awaits it on a dirty export:
// a save that resolved early or on failure would let a stale file ship.
//
// `attempt` is 1 for the initial save and increments on each transient retry. `isSavingRef` stays
// true across the backoff wait so an edit or Сохранить click landing in the gap only QUEUES
// (saveAgainRequested) rather than launching a competing save — and the retry re-serializes the
// editor's CURRENT content, so a keystroke typed during the wait is re-sent, never silently lost.
export function performWrite(
  deps: WriteChainDeps,
  saveVersion: number,
  attempt = 1,
): Promise<void> {
  const { documentId, editor, cycle } = deps
  deps.isSavingRef.current = true
  deps.setIsSaving(true)
  deps.saveAgainRequested.current = false
  // Captured before the round trip: the response's content is the SANITIZED persisted form,
  // and telling whether to adopt it requires knowing what we actually sent.
  const sent = serializeEditorHtml(editor)
  // .then(onFulfilled, onRejected) — NOT .then().catch(): onRejected must handle only THIS
  // attempt's rejection, never the recursive performWrite returned below (its own onRejected owns
  // that). A trailing .catch would run twice for a queued re-save failure, doubling side effects.
  return saveDocument(documentId, sent, saveVersion).then(
    (result) => {
      // Whether to take the server's sanitized form into the editor — rules and rationale live
      // beside the guard that reads the result (autosaveDirtyGuard).
      if (shouldAdoptPersistedContent(sent, serializeEditorHtml(editor), result.content)) {
        editor.commands.setContent(result.content)
      }
      // Read AFTER the adoption decision above: what the editor holds now is what the guard may
      // call saved, and only if the server's copy agrees with it (see autosaveDirtyGuard).
      deps.lastSavedContentRef.current = savedContentAfterResolve(
        serializeEditorHtml(editor),
        result.content,
      )
      deps.setVersion(result.version)
      deps.setSaveError(null)
      if (deps.saveAgainRequested.current) {
        deps.saveAgainRequested.current = false
        // Returned, not fired-and-forgotten: this chain must settle only after the queued re-save
        // does, so an awaiting caller keeps waiting through it and sees its failure.
        return performWrite(deps, result.version)
      }
      cycle.settleClean()
    },
    (error) => {
      // The banner tells the user WHAT happened; this is the only place the underlying error
      // object survives at all. There is no reporting sink, so the console is the whole of the
      // diagnostics — deleting it would leave a failed save with no trace anywhere.
      console.error('Failed to save document', error)
      if (isTransientFailure(error) && attempt < MAX_AUTOSAVE_ATTEMPTS) {
        return retryAfterBackoff(deps, saveVersion, attempt, error)
      }
      cycle.settleFailed(error)
      // Rethrow so an awaiting caller (ExportControl) sees the failure and SKIPS the export —
      // resolving here would ship a stale file. The banner side effects above already ran.
      throw error
    },
  )
}

// A transient failure with attempts left re-fires itself on a capped backoff — no fresh edit and no
// click needed. The cycle stays "saving" across the gap so the retry is the sole writer and any edit
// in the gap only queues. The returned promise keeps the chain OPEN across the wait: an awaiting
// caller sees the ladder's final outcome, not a premature resolve mid-retry.
function retryAfterBackoff(
  deps: WriteChainDeps,
  saveVersion: number,
  attempt: number,
  error: unknown,
): Promise<void> {
  // Same principle settleFailed already applies: a failure that may have LANDED leaves the server's
  // content unknown, so the guard's memory of what the server holds cannot outlive it — otherwise a
  // revert inside the backoff window is suppressed against a memory the failure itself put in doubt,
  // and the editor and the server silently diverge under a «Сохранено» badge. A definite refusal
  // (503) keeps the memory: it is still provably true, and suppressing a redundant re-PUT is right.
  if (mayHaveLandedServerSide(error)) deps.lastSavedContentRef.current = null
  return new Promise<void>((resolve, reject) => {
    deps.cycle.scheduleRetry(attempt, () => {
      // The backoff window is the one place save() cannot apply the guard: isSavingRef is still
      // true, so an edit landing here takes the queue branch and returns before the check. Undo an
      // edit in that gap and the queue now points at content the server already has — firing it
      // would write it again AND chain a second write off the resolve. Fire time is when the
      // question is finally answerable, so ask it here.
      if (isAlreadySaved(serializeEditorHtml(deps.editor), deps.lastSavedContentRef.current)) {
        deps.cycle.settleClean()
        resolve()
        return
      }
      performWrite(deps, saveVersion, attempt + 1).then(resolve, reject)
    })
  })
}
