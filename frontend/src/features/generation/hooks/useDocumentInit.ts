import { useEffect, useRef } from 'react'
import type { Editor } from '@tiptap/react'
import { createDocument, getDocument } from '../api/documentApi'
import type { DocumentType } from '../../../shared/documentTypes'

export const CREATE_FAILED_MESSAGE =
  'Не удалось создать документ. Проверьте соединение и обновите страницу — до этого сохранение недоступно.'
export const LOAD_FAILED_MESSAGE =
  'Не удалось загрузить документ. Проверьте соединение и обновите страницу — до этого сохранение недоступно.'

interface UseDocumentInitParams {
  documentType: DocumentType
  existingDocumentId?: string
  editor: Editor | null
  setDocumentId: (id: string) => void
  setVersion: (version: number) => void
  // Called with user-facing text when init fails, and with `null` when it succeeds.
  //
  // Not optional, and not defaulted: without a documentId, ManualEditor's `handleSave` returns
  // on its first line, so the Save button becomes a permanent no-op and the status line sits on
  // "Создание документа…" forever. Both failures used to end at a `console.error` marked "error
  // surfacing is out of scope for this scenario" — which meant the user typed a whole document
  // into a page that could never persist it and was never told. A required parameter makes a
  // future caller decide what to do rather than inherit silence.
  onError: (message: string | null) => void
}

// Loads an existing document (edit mode) or creates a new one (fresh mode)
// once on mount. Extracted from ManualEditor to keep that component focused
// on rendering/save orchestration.
export function useDocumentInit({
  documentType,
  existingDocumentId,
  editor,
  setDocumentId,
  setVersion,
  onError,
}: UseDocumentInitParams): void {
  // One key per mounted editor, minted once and kept across re-runs of the effect. This is what
  // makes "the same logical create" something the backend can actually recognise.
  //
  // Load-bearing under StrictMode (main.tsx:7), which double-invokes effects in dev: `cancelled`
  // below suppresses the second run's setState but NOT its fetch, so the POST genuinely fires
  // twice. With the key minted inside createDocument those were two distinct keys and the
  // backend created two documents; with one key they are a request and its replay, and the
  // spec's 200 branch collapses them onto one.
  //
  // A ref, not state: it must survive the effect's two invocations without re-rendering, and
  // that window is exactly what it exists to cover.
  const idempotencyKeyRef = useRef<string>('')
  if (!idempotencyKeyRef.current) {
    idempotencyKeyRef.current = crypto.randomUUID()
  }

  useEffect(() => {
    let cancelled = false
    if (existingDocumentId) {
      getDocument(existingDocumentId)
        .then((result) => {
          if (cancelled) return
          setDocumentId(result.documentId)
          setVersion(result.version)
          editor?.commands.setContent(result.content)
          onError(null)
        })
        .catch((error) => {
          if (cancelled) return
          // `documentApi` already built text a person can read; the message is only replaced when
          // it did not (a transport failure carries none). Either way the user learns that this
          // editor cannot save, which is the fact that matters — they are about to type into it.
          onError(error instanceof Error && error.message ? error.message : LOAD_FAILED_MESSAGE)
        })
    } else {
      createDocument(documentType, idempotencyKeyRef.current)
        .then((result) => {
          if (cancelled) return
          setDocumentId(result.documentId)
          // The server's version, not a guess. Omitting this is what left ManualEditor's
          // `useState(1)` to ship on the first PUT and collect a 409 blaming a concurrent save
          // that never happened.
          setVersion(result.version)
          onError(null)
        })
        .catch((error) => {
          if (cancelled) return
          onError(error instanceof Error && error.message ? error.message : CREATE_FAILED_MESSAGE)
        })
    }
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentType, existingDocumentId])
}
