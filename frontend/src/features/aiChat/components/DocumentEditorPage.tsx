import { useParams } from 'react-router-dom'
import { useEditorDocument, LOAD_FAILED_MESSAGE } from '../hooks/useEditorDocument'
import { DocumentNotFoundBlocker } from './DocumentNotFoundBlocker'
import { EditorDocumentView } from './EditorDocumentView'
import { AiChatPanel } from './AiChatPanel'
import './DocumentEditorPage.css'

export const LOADING_MESSAGE = 'Загрузка документа…'

// Thin router between the four states of the load. The two that matter to scenario 0.1 are
// `not-found` (the blocker, and NOTHING else — no editor, no chat) and `ready` (the workspace).
// `failed` is deliberately a different screen from the blocker: see useEditorDocument.
export function DocumentEditorPage() {
  const { documentId } = useParams<{ documentId: string }>()
  const { status, document } = useEditorDocument(documentId ?? '')

  if (status === 'not-found') {
    return <DocumentNotFoundBlocker />
  }

  if (status === 'failed') {
    return (
      <div className="ac-blocker" role="alert" data-testid="document-load-failed">
        <p className="ac-blocker-text">{LOAD_FAILED_MESSAGE}</p>
      </div>
    )
  }

  if (status !== 'ready' || !document) {
    return <p className="ac-loading">{LOADING_MESSAGE}</p>
  }

  return (
    <div className="ac-layout">
      <EditorDocumentView content={document.content} />
      <AiChatPanel />
    </div>
  )
}
