// HTTP client for the manual-document API (POST create — synchronous, no LLM/polling).
export interface CreateDocumentResult {
  documentId: string
  status: string
}

export async function createDocument(documentType: string): Promise<CreateDocumentResult> {
  throw new Error('Not implemented')
}
