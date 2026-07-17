// HTTP client for the generation API (POST create + GET status).
//
// Both calls go through `authorizedRequest`, so every request carries the access token and a
// 401 renews the session and replays it, instead of surfacing as a generation failure the user
// did nothing to cause.
import { authorizedRequest, SessionExpiredError } from '../../auth/api/authorizedRequest'
import { isHttpError, type RequestOptions } from '../../../shared/api/httpClient'
import { DEFAULT_DOCUMENT_TYPE } from '../documentTypes'

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

// The wire is snake_case and this module is the boundary; the rest of the app sees camelCase.
// Declared `unknown`-free but read defensively below — these describe what the backend PROMISES,
// not what a proxy or a partial deploy can actually put on the socket.
interface CreateGenerationWire {
  generation_id: string
  status: string
}

interface GenerationStatusWire extends CreateGenerationWire {
  content: string | null
  topic: string
  volume_pages: number
  document_type: string
  created_at: string
}

// What the user is told when the server refused. `detail` is FastAPI's shape, `message` is the
// auth endpoints' — accept either, since this app talks to both and neither is going away.
function describeFailure(error: unknown, fallback: string): string {
  if (isHttpError(error)) {
    const detail = error.body.detail ?? error.body.message
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
    // No usable text: a non-JSON error page, or a body shaped some third way. The status is the
    // only fact left, and it beats a bare "something went wrong" when someone reports this.
    return `${fallback} (HTTP ${error.status})`
  }
  return error instanceof Error && error.message ? error.message : fallback
}

async function send<T>(path: string, options: RequestOptions, fallback: string): Promise<T> {
  try {
    return await authorizedRequest<T>(path, options)
  } catch (error) {
    // An expired session is NOT a generation failure and must keep its type: the UI shows it as
    // "you are signed out", not as "your document could not be created". Flattening it into a
    // generic Error here would erase the distinction the caller has to make.
    if (error instanceof SessionExpiredError) {
      throw error
    }
    throw new Error(describeFailure(error, fallback))
  }
}

export async function createGeneration(topic: string): Promise<CreateGenerationResult> {
  const data = await send<CreateGenerationWire>(
    '/api/v1/generations',
    {
      method: 'POST',
      // Generated once per call, so an internal 401-retry replays the SAME key and the backend
      // collapses the replay onto the first request instead of billing a second generation.
      headers: { 'Idempotency-Key': crypto.randomUUID() },
      body: {
        document_type: DEFAULT_DOCUMENT_TYPE,
        topic,
        volume_pages: DEFAULT_VOLUME_PAGES,
      },
    },
    'Не удалось создать запрос',
  )
  return { generationId: data.generation_id, status: data.status }
}

export async function getGeneration(id: string): Promise<GenerationStatus> {
  const data = await send<GenerationStatusWire>(
    `/api/v1/generations/${id}`,
    {},
    'Не удалось получить статус',
  )
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
