// The chat history read behind `GET /api/v1/documents/{document_id}/messages` (`endpoints.md:9`).
//
// TDD RED STUB — no implementation. `red-frontend-api`, Story 19, Frontend Scenario 1.1.
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

export async function loadChatMessages(documentId: string): Promise<ChatMessagePage> {
  throw new Error(`Not implemented: loadChatMessages(${documentId})`)
}
