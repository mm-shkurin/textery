// The chat history read behind `GET /api/v1/documents/{document_id}/messages` (`endpoints.md:9`).
//
// Imports `shared/api/send` and NOTHING from a peer feature: follow-up (z) flagged
// `editorDocumentApi.ts:7` pulling `getDocument` out of `generation` as a `frontend-rules.md`
// "Feature Structure" violation, and a second one is not owed to this endpoint — no other feature
// reads this path, so there is no existing loader to wrap.
// One turn of the conversation, in the shape the VIEW reads — the api layer owns it because this
// is where the wire rename lands, and `AiChatPanel` imports it the same way it already imports
// `EditQuotaState` from `editQuotaApi`. It was declared twice until this refactor (here and in
// `AiChatPanel.tsx`, which shipped its copy in `green-frontend` before any read existed), held
// together only by an `expectTypeOf` gate; TypeScript being structural, two copies diverge
// silently — by one growing a field — rather than by any runtime signal.
//
import { send } from '../../../shared/api/send'

// `text` is the only field any ASSERTION reads — `AiChatPanel.history.test.tsx` checks row text
// and nothing else. `messageId` is READ BY THE CODE, as the React key on each row, but pinned by
// no test: both fixtures use distinct ids, so duplicate or absent ids would make React silently
// reuse or drop rows with every layer green. `role` is read by no view yet; it is shaped for
// scenario 1.2, which owns the ordering and the per-side split.
export interface ChatMessage {
  messageId: string
  role: 'user' | 'assistant'
  text: string
}

// A PAGE, not a bare `ChatMessage[]`. The endpoint is keyset-paginated by contract, so an array
// alone would assert "this is the whole conversation" — a claim the wire never makes — and
// scenario 1.2 would have to widen a shipped return type to say otherwise.
export interface ChatMessagePage {
  messages: ChatMessage[]
  nextCursor: string | null
}

// Deliberately NOT `{ notFound: true }`. `error_code: 'NOT_FOUND'` is shared by all seven
// endpoints, and a 404 reaching the HISTORY read while the document itself loaded is the history
// endpoint failing — not "your document is gone". `loadEditorDocument` is the authoritative read
// and already opts in; a second typed 404 here would blank the whole editor over a broken sidebar.
const FALLBACK = 'Не удалось загрузить историю чата'

// The wire shape as UNKNOWN keys, not as a declared response type: a declared type is a promise
// the server makes, and every guard below exists because the server can break it.
interface MessagePageWire {
  items?: unknown
  next_cursor?: unknown
}

// Typed against the union rather than inferred as `string[]`, and narrowed by a predicate rather
// than by a cast: a cast would keep compiling if `ChatMessage['role']` ever gained a value this
// list did not, and would be an outright lie in the other direction. With both tied together,
// either drift is a compile error rather than a page silently refused at runtime.
const ROLES: readonly ChatMessage['role'][] = ['user', 'assistant']

function isRole(value: unknown): value is ChatMessage['role'] {
  return typeof value === 'string' && (ROLES as readonly string[]).includes(value)
}

// Silence must REFUSE. `performRequest` ends with `res.json().catch(() => ({}))`, so a 204, an
// empty 200 and a proxy's HTML page served with a 200 all arrive as `{}` — and `items ?? []`
// would answer "this document has never been edited" for an endpoint that said nothing.
function mapMessage(row: unknown): ChatMessage {
  if (typeof row !== 'object' || row === null) {
    throw new Error(FALLBACK)
  }
  const { message_id: messageId, role, text } = row as Record<string, unknown>
  if (typeof messageId !== 'string' || typeof text !== 'string') {
    throw new Error(FALLBACK)
  }
  // Against the ENUM, not merely against `string`: scenario 1.2 splits the conversation on this
  // field, and a third value would silently pick a side.
  if (!isRole(role)) {
    throw new Error(FALLBACK)
  }
  return { messageId, role, text }
}

// `nextCursor` is `string | null` by declaration, so the wire has to keep that promise: absent and
// null are the contract's two "last page" spellings, anything else is the endpoint failing to
// state a page. A pass-through rename would type an arbitrary value `string` and scenario 1.2
// would interpolate `[object Object]` into a query string.
function mapCursor(nextCursor: unknown): string | null {
  if (nextCursor === undefined || nextCursor === null) {
    return null
  }
  if (typeof nextCursor !== 'string') {
    throw new Error(FALLBACK)
  }
  return nextCursor
}

function mapPage(body: MessagePageWire): ChatMessagePage {
  // The page itself is object-checked for the same reason each ROW is. `performRequest` substitutes
  // `{}` only when `res.json()` THROWS; a body of literal `null` parses fine and arrives as `null`,
  // so reading `body.items` off it raises a TypeError — an untyped English escape past the
  // invariant every other refusal here keeps, and past the plain `Error` scenario 1.3 is told to
  // treat as its signal.
  if (typeof body !== 'object' || body === null) {
    throw new Error(FALLBACK)
  }
  if (!Array.isArray(body.items)) {
    throw new Error(FALLBACK)
  }
  return {
    messages: body.items.map(mapMessage),
    nextCursor: mapCursor(body.next_cursor),
  }
}

// No query string: `limit` is server-defaulted by the contract and `cursor` is by definition
// absent on the first page, so spelling either out states a policy the contract already owns.
export async function loadChatMessages(documentId: string): Promise<ChatMessagePage> {
  return mapPage(
    await send<MessagePageWire>(`/api/v1/documents/${documentId}/messages`, {}, FALLBACK),
  )
}
