// Owner-scoped history: the two list endpoints behind "Мои работы". Both go through `send` ->
// `authorizedRequest`, so the token travels and a 401 renews and replays. There is no anonymous
// history by construction — the backend scopes both lists to the bearer's user.
//
// Contract measured by curl against the live stack 2026-07-17, not read from a spec:
//   GET /api/v1/documents?limit=2          -> {"items":[…2], "next_cursor":"<base64>"}
//   GET /api/v1/documents?limit=2&cursor=… -> {"items":[…1], "next_cursor":null}   <- null = end
//   GET /api/v1/documents (new user)       -> {"items":[], "next_cursor":null}
//   ?cursor=garbage                        -> 400 {"error_code":"INVALID_CURSOR"}
//   ?limit=0 and ?limit=999                -> 400   (bounds enforced; 20 is the server default)
//   no token                               -> 401 {"error_code":"UNAUTHORIZED"}
import { send } from './send'

// One page of either list. `nextCursor === null` means the end — not an error, and not an empty
// page: the last page carries items AND a null cursor, so paging must stop on the cursor, never
// on an empty `items`.
export interface Page<T> {
  items: T[]
  nextCursor: string | null
}

interface PageWire<T> {
  items: T[]
  next_cursor: string | null
}

// List items carry metadata only — no `content`. That is right for a list, and it means opening
// an entry still costs a GET /documents/{id}.
export interface DocumentSummary {
  documentId: string
  documentType: string
  status: string
  version: number
  createdAt: string
  updatedAt: string
}

interface DocumentSummaryWire {
  document_id: string
  document_type: string
  status: string
  version: number
  created_at: string
  updated_at: string
}

// The generations list returns the same DTO the create call does (PageDto_GenerationCreatedDto_),
// which carries `topic` and `created_at` — enough to render a row. Worth stating because
// `generationApi.ts`'s CreateGenerationWire declares only {generation_id, status} and discards
// the rest: that narrower view is the create path's business, not the wire's shape.
export interface GenerationSummary {
  generationId: string
  status: string
  topic: string
  documentType: string
  volumePages: number
  createdAt: string
}

interface GenerationSummaryWire {
  generation_id: string
  status: string
  topic: string
  document_type: string
  volume_pages: number
  created_at: string
}

// `cursor` is an opaque base64 keyset token (`<timestamp>|<uuid>` at the time of writing).
// Deliberately passed through untouched: decoding it here would couple the client to an
// encoding the contract never promised.
function pagePath(base: string, limit: number, cursor?: string): string {
  const params = new URLSearchParams({ limit: String(limit) })
  if (cursor) params.set('cursor', cursor)
  return `${base}?${params.toString()}`
}

export async function listDocuments(limit = 20, cursor?: string): Promise<Page<DocumentSummary>> {
  const data = await send<PageWire<DocumentSummaryWire>>(
    pagePath('/api/v1/documents', limit, cursor),
    {},
    'Не удалось загрузить документы',
  )
  return {
    items: data.items.map((item) => ({
      documentId: item.document_id,
      documentType: item.document_type,
      status: item.status,
      version: item.version,
      createdAt: item.created_at,
      updatedAt: item.updated_at,
    })),
    nextCursor: data.next_cursor,
  }
}

export async function listGenerations(
  limit = 20,
  cursor?: string,
): Promise<Page<GenerationSummary>> {
  const data = await send<PageWire<GenerationSummaryWire>>(
    pagePath('/api/v1/generations', limit, cursor),
    {},
    'Не удалось загрузить генерации',
  )
  return {
    items: data.items.map((item) => ({
      generationId: item.generation_id,
      status: item.status,
      topic: item.topic,
      documentType: item.document_type,
      volumePages: item.volume_pages,
      createdAt: item.created_at,
    })),
    nextCursor: data.next_cursor,
  }
}
