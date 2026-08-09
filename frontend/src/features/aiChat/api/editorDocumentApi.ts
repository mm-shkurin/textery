// The editor's read of /documents/{id}. A thin wrapper over the ONE existing loader rather than a
// second fetch: `send` flattens every non-401/409 refusal into a described generic Error, so by the
// time a wrapper regained control a 404 and a 500 would be the same value — recovering the
// distinction outside `send` would have meant re-implementing the token attach, the 401
// renew-and-replay and the refusal-describing. So the 404 branch lives beside the 409 one, and this
// module only asks for it (`{ notFound: true }`) and drops what the editor does not use.
import { getDocument } from '../../generation/api/documentApi'

// Re-exported, NOT re-declared: two structurally identical classes are two different identities,
// and `instanceof` in useEditorDocument / DocumentEditorPage would silently go false.
export { DocumentNotFoundError } from '../../../shared/api/send'

// `status` is deliberately absent: the editor renders `content` and sends `version` back on save,
// and nothing in this feature branches on the document's status.
export interface EditorDocument {
  documentId: string
  content: string
  version: number
}

export async function loadEditorDocument(documentId: string): Promise<EditorDocument> {
  const document = await getDocument(documentId, { notFound: true })
  return {
    documentId: document.documentId,
    content: document.content,
    version: document.version,
  }
}
