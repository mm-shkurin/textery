// HTTP client for the manual-document API (POST create — synchronous, no LLM/polling).
import { API_BASE, request } from './httpClient'

export interface CreateDocumentResult {
  documentId: string
  status: string
}

// RED plumbing only: `idempotencyKey` identifies the logical create so retries can replay
// it (documents_create.yaml's 200 branch). Accepted but deliberately unused — wiring it to
// the header is GREEN's job. See documentApi.contract.test.ts.
export async function createDocument(
  documentType: string,
  _idempotencyKey?: string
): Promise<CreateDocumentResult> {
  const data = (await request(
    `${API_BASE}/api/v1/documents`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Idempotency-Key': crypto.randomUUID(),
      },
      body: JSON.stringify({
        document_type: documentType,
        content: '',
      }),
    },
    'Не удалось создать документ'
  )) as { document_id: string; status: string }
  return { documentId: data.document_id, status: data.status }
}

export interface SaveDocumentResult {
  status: string
  version: number
}

export async function saveDocument(
  documentId: string,
  content: string,
  version: number
): Promise<SaveDocumentResult> {
  const data = (await request(
    `${API_BASE}/api/v1/documents/${documentId}`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        content,
        version,
      }),
    },
    'Не удалось сохранить документ'
  )) as { status: string; version: number }
  return { status: data.status, version: data.version }
}

export interface GetDocumentResult {
  documentId: string
  status: string
  content: string
  version: number
}

export async function getDocument(documentId: string): Promise<GetDocumentResult> {
  const data = (await request(
    `${API_BASE}/api/v1/documents/${documentId}`,
    {
      method: 'GET',
    },
    'Не удалось загрузить документ'
  )) as { document_id: string; status: string; content: string; version: number }
  return {
    documentId: data.document_id,
    status: data.status,
    content: data.content,
    version: data.version,
  }
}
