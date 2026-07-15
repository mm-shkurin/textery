import { useEffect } from 'react'
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
      createDocument(documentType)
        .then((result) => {
          if (!cancelled) setDocumentId(result.documentId)
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
