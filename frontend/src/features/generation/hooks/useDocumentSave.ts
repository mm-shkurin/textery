import { useRef, useState } from 'react'
import type { Editor } from '@tiptap/react'
import { saveDocument } from '../api/documentApi'
import { SessionExpiredError } from '../../auth/api/authorizedRequest'
import { VersionConflictError } from '../../../shared/api/send'

export const SAVE_ERROR_MESSAGE =
  'Не удалось сохранить. Повторите — текст пока только в редакторе, не потеряйте вкладку.'

// Deliberately does NOT say "попробуйте ещё раз": retrying is what just failed. Reopening is the
// only action that can succeed, and it costs the text in this editor — so the message says that
// outright rather than letting the user discover it by losing the paragraph twice.
export const CONFLICT_ERROR_MESSAGE =
  'Документ был изменён другим сохранением. Откройте его заново, чтобы увидеть актуальную версию — текст в этом редакторе не сохранён.'

// What a failed save says. The default is for a network blip: retrying may recover, so it asks for
// that — but it does NOT reassure the text is "сохранён локально": there is no persistence anywhere
// (content lives only in Tiptap's in-memory state), so it warns the tab is the only copy instead.
//
// An expired session is not a failure of the save: the request was fine, the user is signed out.
// `authorizedRequest` raises SessionExpiredError precisely so callers can tell the two apart, and
// `send` goes out of its way to rethrow it untouched — but NOTHING narrowed it, so the whole
// carve-out was unconsumed machinery and this catch flattened it right back into "check your
// connection", telling a signed-out user to retry a button that cannot work until they sign in.
// Its own message ("Сессия истекла. Войдите снова.") is the accurate thing to show.
//
// A VersionConflictError reaching here is the same mistake one branch over. `saveDocument` already
// answers the FIRST 409 by refetching the version and retrying, so anything that arrives here has
// survived that — a second writer landed during the retry, or the refetch itself failed. The
// connection is not the problem, and reassuring the user their text is safe would be a promise this
// branch cannot keep: another save holds the document, and the next click re-enters the same race.
// Saying so lets the user reopen the document instead of clicking a button that will lose again.
function describeSaveFailure(error: unknown): string {
  if (error instanceof SessionExpiredError) return error.message
  if (error instanceof VersionConflictError) return CONFLICT_ERROR_MESSAGE
  return SAVE_ERROR_MESSAGE
}

interface UseDocumentSaveParams {
  documentId: string | null
  editor: Editor | null
  initialVersion?: number
  onSaved: () => void
  onDirty: () => void
}

export interface DocumentSave {
  isSaving: boolean
  saveError: string | null
  version: number
  setVersion: (version: number) => void
  // Call on every edit: an edit landing mid-flight has to queue a re-save.
  noteEdit: () => void
  // Resolves only after the save (and any queued re-save) fully completes, and REJECTS on failure.
  // ExportControl awaits this on a dirty export: a save that resolved on failure would let a stale
  // file ship, so the failure must propagate. The Save button consumes it fire-and-forget.
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
  initialVersion = 1,
  onSaved,
  onDirty,
}: UseDocumentSaveParams): DocumentSave {
  const [version, setVersion] = useState(initialVersion)
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const isSavingRef = useRef(false)
  const saveAgainRequested = useRef(false)
  // The promise of the currently in-flight save chain (including any queued re-save it spawns). A
  // second save() call while one is running returns THIS, not an already-resolved promise, so a
  // caller awaiting it (ExportControl on a dirty export) waits for the real persistence to settle.
  const inFlightRef = useRef<Promise<void> | null>(null)

  const performSave = (saveVersion: number): Promise<void> => {
    if (!documentId || !editor) return Promise.resolve()
    isSavingRef.current = true
    setIsSaving(true)
    saveAgainRequested.current = false
    // Captured before the round trip: the response's content is the SANITIZED persisted form,
    // and telling whether to adopt it requires knowing what we actually sent.
    const sent = editor.getHTML()
    // .then(onFulfilled, onRejected) — NOT .then().catch(): onRejected must handle only THIS
    // save's rejection, never the recursive performSave returned below (its own onRejected owns
    // that). A trailing .catch would run twice for a queued re-save failure, doubling side effects.
    return saveDocument(documentId, sent, saveVersion).then(
      (result) => {
        // The server's content is the source of truth — it strips <script> with its contents and
        // normalises void tags (`<br />` -> `<br>`), measured 2026-07-17. Keeping ours would
        // render markup the server does not have and re-send it on every later save.
        //
        // But adopt ONLY if the editor still holds exactly what we sent. Typing continues while
        // the request is in flight, and setContent would delete those keystrokes — the worst
        // possible trade for cosmetic agreement. If it changed, the next save re-sanitizes
        // anyway, so nothing is lost by skipping.
        if (result.content !== sent && editor.getHTML() === sent) {
          editor.commands.setContent(result.content)
        }
        setVersion(result.version)
        setSaveError(null)
        if (saveAgainRequested.current) {
          saveAgainRequested.current = false
          // Return the re-save so this chain settles only after it does — the awaiting caller
          // keeps waiting through the queued save, and its failure propagates out of here.
          return performSave(result.version)
        }
        isSavingRef.current = false
        setIsSaving(false)
        onSaved()
      },
      (error) => {
        // The banner tells the user WHAT happened; this is the only place the underlying error
        // object survives at all. There is no reporting sink, so the console is the whole of the
        // diagnostics — deleting it would leave a failed save with no trace anywhere.
        console.error('Failed to save document', error)
        // Don't auto-retry a queued edit after a real error (out of scope: that's
        // autosave-retry behavior). Drop the queued flag so a stale retry doesn't
        // fire later, but keep the user's latest content in the editor untouched
        // so they can manually retry by clicking Save again.
        saveAgainRequested.current = false
        isSavingRef.current = false
        setIsSaving(false)
        setSaveError(describeSaveFailure(error))
        // Rethrow so an awaiting caller (ExportControl) sees the failure and SKIPS the export —
        // resolving here would ship a stale file. The banner side effects above already ran.
        throw error
      },
    )
  }

  return {
    isSaving,
    saveError,
    version,
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
        // Return the in-flight chain, not a resolved promise: the queued re-save is folded into it
        // (its resolve handler runs performSave again), so awaiting this waits for that too.
        return inFlightRef.current ?? Promise.resolve()
      }
      const promise = performSave(version)
      inFlightRef.current = promise
      return promise
    },
  }
}
