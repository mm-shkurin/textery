// HTTP client for the generation API (POST create + GET status).
//
// Both calls go through `send`, and therefore `authorizedRequest`, so every request carries the
// access token and a 401 renews the session and replays it, instead of surfacing as a generation
// failure the user did nothing to cause.
import { send } from '../../../shared/api/send'
import { EMPTY_PARAMETERS, type GenerationParameters } from '../generationParameters'
import {
  DEFAULT_DOCUMENT_TYPE,
  WIRE_DOCUMENT_TYPE,
  type DocumentType,
} from '../../../shared/documentTypes'

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

// `documentType` is optional with a default rather than required, and that is a constraint, not
// a preference: five sibling call sites in `generationApi.test.ts` and the useGeneration suite
// call this with one argument, and test files are read-only in the green phase — a required
// parameter would break the typecheck in files this phase may not touch. The hazard of an
// optional default (green passes while the picked type is never actually threaded through) is
// closed instead by a caller-level test: `useFlowNavigation.documentType.test.tsx` drives
// `selectType('referat')` → `submitGeneration` and asserts THIS function receives 'referat'.
export async function createGeneration(
  topic: string,
  documentType: DocumentType = DEFAULT_DOCUMENT_TYPE,
  // Defaulted for the same read-only-tests reason `documentType` is, and because an untouched
  // form must still send what the client sent before these fields existed.
  parameters: GenerationParameters = EMPTY_PARAMETERS,
): Promise<CreateGenerationResult> {
  const data = await send<CreateGenerationWire>(
    '/api/v1/generations',
    {
      method: 'POST',
      // Generated once per call, so an internal 401-retry replays the SAME key and the backend
      // collapses the replay onto the first request instead of billing a second generation.
      headers: { 'Idempotency-Key': crypto.randomUUID() },
      body: {
        // The wire type is Cyrillic ("доклад"); the backend rejects the app value ("doklad")
        // with 422 INVALID_DOCUMENT_TYPE. Map here, same as documentApi.createDocument does.
        document_type: WIRE_DOCUMENT_TYPE[documentType],
        topic,
        volume_pages: parameters.volumePages,
        // Omitted rather than sent as "": the contract types both as optional, and an empty
        // string is a value the user chose to leave blank — which the prompt builder would then
        // have to re-interpret as absence. Deciding it here keeps one meaning of "not filled in".
        ...(parameters.requirements.trim() ? { requirements: parameters.requirements.trim() } : {}),
        ...(parameters.extraWishes.trim() ? { extra_wishes: parameters.extraWishes.trim() } : {}),
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
