// HTTP client for the generation API (POST create + GET status).
// Base URL defaults to '' so requests go through the Vite dev proxy (/api → backend).
import { DEFAULT_DOCUMENT_TYPE } from '../documentTypes'

const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? ''

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
