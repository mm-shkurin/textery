// HTTP client for the generation API (POST create + GET status).
// Base URL defaults to '' so requests go through the Vite dev proxy (/api → backend).
import { DEFAULT_DOCUMENT_TYPE } from '../documentTypes'
import { API_BASE, readErrorMessage } from './httpClient'

// No UI control exists yet for volume — every request asks for a fixed 5-page document
// until the product adds a page-count selector.
const DEFAULT_VOLUME_PAGES = 5

export interface CreateGenerationResult {
  generationId: string
  status: string
}

export interface GenerationStatus {
  generationId: string
  status: string
  content: string | null
  topic: string
  volumePages: number
  documentType: string
  createdAt: string
}

export async function createGeneration(topic: string): Promise<CreateGenerationResult> {
  const res = await fetch(`${API_BASE}/api/v1/generations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': crypto.randomUUID(),
    },
    body: JSON.stringify({
      document_type: DEFAULT_DOCUMENT_TYPE,
      topic,
      volume_pages: DEFAULT_VOLUME_PAGES,
    }),
  })
  if (!res.ok) {
    throw new Error(await readErrorMessage(res, 'Не удалось создать запрос'))
  }
  const data = await res.json()
  return { generationId: data.generation_id, status: data.status }
}

export async function getGeneration(id: string): Promise<GenerationStatus> {
  const res = await fetch(`${API_BASE}/api/v1/generations/${id}`)
  if (!res.ok) {
    throw new Error(await readErrorMessage(res, 'Не удалось получить статус'))
  }
  const data = await res.json()
  return {
    generationId: data.generation_id,
    status: data.status,
    content: data.content ?? null,
    topic: data.topic,
    volumePages: data.volume_pages,
    documentType: data.document_type,
    createdAt: data.created_at,
  }
}
