import { useEffect, useRef, useState } from 'react'
import {
  DocumentNotFoundError,
  loadEditorDocument,
  type EditorDocument,
} from '../api/editorDocumentApi'

export const LOAD_FAILED_MESSAGE =
  'Не удалось загрузить документ. Проверьте соединение и обновите страницу.'

export type EditorDocumentStatus = 'loading' | 'ready' | 'not-found' | 'failed'

export interface EditorDocumentState {
  status: EditorDocumentStatus
  document: EditorDocument | null
}

// Loads the document behind `/documents/:documentId` exactly once.
//
// ONLY DocumentNotFoundError becomes `not-found`. A bare `catch { setNotFound(true) }` would
// answer a 500, an expired session or a dropped connection with "Документ не найден" — telling
// the user their document is gone and inviting them to re-create one that exists. Everything
// that is not the 404 lands on `failed`, which says the truth: the load did not work, try again.
export function useEditorDocument(documentId: string): EditorDocumentState {
  const [state, setState] = useState<EditorDocumentState>({ status: 'loading', document: null })

  // Which id has already been requested. StrictMode (main.tsx) double-invokes effects in dev, so
  // without this the load fires twice per mount. A cleanup-flag guard (the pattern in
  // useDocumentInit) suppresses the second run's setState but NOT its fetch — here the fetch
  // itself must not repeat, so the guard sits before it.
  //
  // It doubles as the stale-response check: a response whose id is no longer the requested one is
  // dropped instead of overwriting a newer document.
  const requestedIdRef = useRef<string | null>(null)

  useEffect(() => {
    if (requestedIdRef.current === documentId) return
    requestedIdRef.current = documentId
    setState({ status: 'loading', document: null })

    loadEditorDocument(documentId)
      .then((document) => {
        if (requestedIdRef.current !== documentId) return
        setState({ status: 'ready', document })
      })
      .catch((error: unknown) => {
        if (requestedIdRef.current !== documentId) return
        const status = error instanceof DocumentNotFoundError ? 'not-found' : 'failed'
        setState({ status, document: null })
      })
  }, [documentId])

  return state
}
