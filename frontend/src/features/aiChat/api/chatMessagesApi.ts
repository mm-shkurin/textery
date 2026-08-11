// The chat history read behind `GET /api/v1/documents/{document_id}/messages` (`endpoints.md:9`).
//
// TDD RED STUB — no implementation. `red-frontend-api`, Story 19, Frontend Scenario 1.1.
//
// Imports `shared/api/send` and NOTHING from a peer feature: follow-up (z) flagged
// `editorDocumentApi.ts:7` pulling `getDocument` out of `generation` as a `frontend-rules.md`
// "Feature Structure" violation, and a second one is not owed to this endpoint — no other feature
// reads this path, so there is no existing loader to wrap.
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
