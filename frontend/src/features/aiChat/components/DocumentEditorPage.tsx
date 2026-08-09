import { useParams } from 'react-router-dom'
import { useEditorDocument } from '../hooks/useEditorDocument'
import { DocumentNotFoundBlocker } from './DocumentNotFoundBlocker'
import { EditorDocumentView } from './EditorDocumentView'
import { AiChatPanel } from './AiChatPanel'
import './DocumentEditorPage.css'

// Both strings live beside the markup that renders them. LOAD_FAILED_MESSAGE used to sit in
// useEditorDocument, which never displayed it — and shares its name with a differently-worded
// constant in generation/hooks/useDocumentInit, so two hooks exporting it invited the wrong import.
export const LOADING_MESSAGE = 'Загрузка документа…'
export const LOAD_FAILED_MESSAGE =
  'Не удалось загрузить документ. Проверьте соединение и обновите страницу.'

// Thin router between the four states of the load. The two that matter to scenario 0.1 are
// `not-found` (the blocker, and NOTHING else — no editor, no chat) and `ready` (the workspace).
// `failed` is deliberately a different screen from the blocker: see useEditorDocument.
export function DocumentEditorPage() {
  const { documentId } = useParams<{ documentId: string }>()
  const state = useEditorDocument(documentId ?? '')

  if (state.status === 'not-found') {
    return <DocumentNotFoundBlocker />
  }

  if (state.status === 'failed') {
    return (
      <div className="ac-blocker" role="alert" data-testid="document-load-failed">
        <p className="ac-blocker-text">{LOAD_FAILED_MESSAGE}</p>
      </div>
    )
  }

  if (state.status !== 'ready') {
    return <p className="ac-loading">{LOADING_MESSAGE}</p>
  }

  return (
    <div className="ac-layout">
      <EditorDocumentView content={state.document.content} />
      <AiChatPanel />
    </div>
  )
}
