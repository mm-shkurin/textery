import { useEffect, useRef } from 'react'
import type { Editor } from '@tiptap/react'
import { createDocument, getDocument } from '../api/documentApi'
import type { DocumentType } from '../documentTypes'

interface UseDocumentInitParams {
  documentType: DocumentType
  existingDocumentId?: string
  editor: Editor | null
  setDocumentId: (id: string) => void
  setVersion: (version: number) => void
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
        })
        .catch((error) => {
          // Error surfacing (retry/UI state) is out of scope for this scenario;
          // logging keeps the failure from being silently swallowed.
          console.error('Failed to load document', error)
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
        })
        .catch((error) => {
          // Error surfacing (retry/UI state) is out of scope for this scenario;
          // logging keeps the failure from being silently swallowed.
          console.error('Failed to create document', error)
        })
    }
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentType, existingDocumentId])
}
