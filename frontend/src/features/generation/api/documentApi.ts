// HTTP client for the manual-document API (create / read / save — synchronous, no LLM/polling).
//
// Every call goes through `send` → `authorizedRequest`, so it carries the access token and a 401
// renews the session and replays rather than surfacing as a document failure the user did not
// cause. Manual mode is behind a session by product decision (2026-07-17): an unauthorized
// visitor can neither generate nor write.
import { send } from './send'

interface DocumentWire {
  document_id: string
  status: string
  content: string
  version: number
}

export interface CreateDocumentResult {
  documentId: string
  status: string
  version: number
}

// `version` is REQUIRED, not optional, and that is the point: it is the optimistic-concurrency
// token the next PUT must carry (documents_create.yaml). An optional field would let a caller
// fall back to a guess — which is exactly the bug this replaced, where the create response's
// version was parsed away and `useState(1)` shipped in its place, earning a 409 that blamed a
// concurrent save that never happened.
//
// `idempotencyKey` is REQUIRED for the same reason. Minting it inside this function made the
// spec's 200-replay branch unreachable by construction: every call sent a fresh key, so no
// replay could ever be recognised. The caller owns it because only the caller knows what "the
// same logical create" means — see useDocumentInit, where one mount must survive StrictMode's
// double-invoked effect as ONE document.
export async function createDocument(
  documentType: string,
  idempotencyKey: string,
): Promise<CreateDocumentResult> {
  const data = await send<DocumentWire>(
    '/api/v1/documents',
    {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      // document_type is the ONLY field. `content` is server-owned; sending it is a 422
      // ("a request body containing a server-owned field"), which is why no document was ever
      // created against a conformant backend.
      body: { document_type: documentType },
    },
    'Не удалось создать документ',
  )
  return { documentId: data.document_id, status: data.status, version: data.version }
}

export interface SaveDocumentResult {
  status: string
  version: number
}

export async function saveDocument(
  documentId: string,
  content: string,
  version: number,
): Promise<SaveDocumentResult> {
  const data = await send<DocumentWire>(
    `/api/v1/documents/${documentId}`,
    {
      method: 'PUT',
      body: { content, version },
    },
    'Не удалось сохранить документ',
  )
  return { status: data.status, version: data.version }
}

export interface GetDocumentResult {
  documentId: string
  status: string
  content: string
  version: number
}

export async function getDocument(documentId: string): Promise<GetDocumentResult> {
  const data = await send<DocumentWire>(
    `/api/v1/documents/${documentId}`,
    {},
    'Не удалось загрузить документ',
  )
  return {
    documentId: data.document_id,
    status: data.status,
    content: data.content,
    version: data.version,
  }
}
