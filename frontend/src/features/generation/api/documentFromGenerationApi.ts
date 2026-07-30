// The one NEW endpoint story 18 adds (documents_from_generation.yaml): a completed, caller-owned
// generation becomes an editable Document, its markdown-ish body converted to sanitized HTML
// server-side. Two additive fields over the shared story-5 DocumentResponse — `generation_id` and
// `title` (server-derived at conversion).
//
// It lives in its OWN module rather than beside its four siblings in documentApi.ts for a boring
// mechanical reason worth recording: documentApi.ts stood at 182 lines against a 200-line hard
// limit, and this function plus its type is 35. The choice was to split or to delete explanation
// from the four existing clients to make room, and comments that were paid for by measured bugs
// are worth more than co-location. `documentApi` re-exports both names, so callers (and the wire
// test) still import from there.
import { send } from '../../../shared/api/send'

// The wire body, narrowed to the six fields this client surfaces. `document_type`, `created_at` and
// `updated_at` are documented on the response and deliberately absent: nothing in the app reads
// them, and declaring them would invite a green that spreads the wire object through.
interface DocumentFromGenerationWire {
  document_id: string
  generation_id: string
  title: string
  status: string
  content: string
  version: number
}

// `generationId` is NON-nullable here, unlike the shared story-5 `generation_id` it comes from:
// null is what a MANUALLY created document reports, and this endpoint cannot produce one — it
// exists only to convert a generation, so the id it echoes back is always the id that was sent.
export interface DocumentFromGenerationResult {
  documentId: string
  generationId: string
  title: string
  status: string
  content: string
  version: number
}

// `idempotencyKey` is a required parameter for the same reason it is on `createDocument`: minting
// it inside would make the spec's replay branch unreachable by construction. Here the stake is
// higher — the caller is a POLL LOOP, not a click, so "the same logical conversion" is a judgement
// only the caller can make.
export async function createDocumentFromGeneration(
  generationId: string,
  idempotencyKey: string,
): Promise<DocumentFromGenerationResult> {
  // No `status === 201` branch on purpose. 201 and 200 are the SAME success — a fresh conversion
  // vs. an idempotent replay or a lost insert race the UNIQUE constraint on Document.generation_id
  // resolves — and both hand back the document the user must now edit. `send` returns only the
  // parsed body, so this client is status-agnostic by construction and must stay that way.
  const data = await send<DocumentFromGenerationWire>(
    '/api/v1/documents/from-generation',
    {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      // `generation_id` is the ONLY field the endpoint accepts. Server-owned fields sent alongside
      // it (title, status, version) are IGNORED rather than honoured, so sending them would be a
      // claim of ownership this client does not have.
      body: { generation_id: generationId },
    },
    'Не удалось открыть сгенерированный документ',
  )
  return {
    documentId: data.document_id,
    generationId: data.generation_id,
    title: data.title,
    status: data.status,
    content: data.content,
    version: data.version,
  }
}
