// HTTP client for the manual-document API (POST create — synchronous, no LLM/polling).
const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? ''

export interface CreateDocumentResult {
  documentId: string
  status: string
}

async function readErrorMessage(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json()
    const detail = body?.detail ?? body?.message
    if (typeof detail === 'string' && detail.trim()) return detail
  } catch {
    // body isn't JSON or is empty — fall through to fallback
  }
  return `${fallback} (HTTP ${res.status})`
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
