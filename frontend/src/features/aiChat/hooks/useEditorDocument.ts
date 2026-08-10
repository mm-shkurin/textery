import { useEffect, useRef, useState } from 'react'
import {
  DocumentNotFoundError,
  loadEditorDocument,
  type EditorDocument,
} from '../api/editorDocumentApi'

export type EditorDocumentStatus = 'loading' | 'ready' | 'not-found' | 'failed'

// A union rather than `{ status; document: EditorDocument | null }`: only `ready` has a document,
// and the loose shape forced every reader to re-check for a null the hook never produces in that
// state — a branch no test can reach because no code path creates it.
export type EditorDocumentState =
  { status: Exclude<EditorDocumentStatus, 'ready'> } | { status: 'ready'; document: EditorDocument }

// Loads the document behind `/documents/:documentId` exactly once.
//
// ONLY DocumentNotFoundError becomes `not-found`. A bare `catch { setNotFound(true) }` would
// answer a 500, an expired session or a dropped connection with "Документ не найден" — telling
// the user their document is gone and inviting them to re-create one that exists. Everything
// that is not the 404 lands on `failed`, which says the truth: the load did not work, try again.
export function useEditorDocument(documentId: string): EditorDocumentState {
  const [state, setState] = useState<EditorDocumentState>({ status: 'loading' })

  // Which id has already been requested. StrictMode (main.tsx) double-invokes effects in dev, so
  // without this the load fires twice per mount. A cleanup-flag guard (the pattern in
  // useDocumentInit) suppresses the second run's setState but NOT its fetch — here the fetch
  // itself must not repeat, so the guard sits before it.
  //
  const requestedIdRef = useRef<string | null>(null)

  // Which *request* is current, not which id. Route ping-pong A → B → A issues two fetches for A,
  // and by the time the first one resolves the id ref is back to `A` — so an id comparison lets the
  // superseded response install a stale `version`, which travels back to the server on the next
  // save. Each effect run takes the next token and only the holder of the current one may setState.
  const requestTokenRef = useRef(0)

  useEffect(() => {
    if (requestedIdRef.current === documentId) return
    requestedIdRef.current = documentId
    const requestToken = ++requestTokenRef.current
    setState({ status: 'loading' })

    loadEditorDocument(documentId)
      .then((document) => {
        if (requestTokenRef.current !== requestToken) return
        setState({ status: 'ready', document })
      })
      .catch((error: unknown) => {
        if (requestTokenRef.current !== requestToken) return
        setState({ status: error instanceof DocumentNotFoundError ? 'not-found' : 'failed' })
      })
  }, [documentId])

  return state
}
