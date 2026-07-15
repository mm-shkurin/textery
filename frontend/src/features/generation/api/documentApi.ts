// HTTP client for the manual-document API (POST create — synchronous, no LLM/polling).
import { API_BASE, readErrorMessage } from './httpClient'

export interface CreateDocumentResult {
  documentId: string
  status: string
}

export async function createDocument(documentType: string): Promise<CreateDocumentResult> {
  const res = await fetch(`${API_BASE}/api/v1/documents`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': crypto.randomUUID(),
    },
    body: JSON.stringify({
      document_type: documentType,
      content: '',
    }),
  })
  if (!res.ok) {
    throw new Error(await readErrorMessage(res, 'Не удалось создать документ'))
  }
  const data = await res.json()
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
  const res = await fetch(`${API_BASE}/api/v1/documents/${documentId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      content,
      version,
    }),
  })
  if (!res.ok) {
    throw new Error(await readErrorMessage(res, 'Не удалось сохранить документ'))
  }
  const data = await res.json()
  return { status: data.status, version: data.version }
}
