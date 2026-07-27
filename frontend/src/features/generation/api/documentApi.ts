// HTTP client for the manual-document API (create / read / save — synchronous, no LLM/polling).
//
// Every call goes through `send` → `authorizedRequest`, so it carries the access token and a 401
// renews the session and replays rather than surfacing as a document failure the user did not
// cause. Manual mode is behind a session by product decision (2026-07-17): an unauthorized
// visitor can neither generate nor write.
import { send, VersionConflictError } from '../../../shared/api/send'
import { WIRE_DOCUMENT_TYPE, type DocumentType } from '../../../shared/documentTypes'

// FAIL-CLOSED CONTRACT (H9.5). `version` is the optimistic-concurrency token every subsequent PUT
// must carry. `send<DocumentWire>` casts the JSON blindly, so a response whose `version` is absent,
// null, or unparseable would flow into the caller's version state and be PUT on the next autosave —
// a write no longer guarded by the token it claims, i.e. the silent overwrite the hazard forbids.
// Exported so the test asserts against ONE definition of the message, never a drifting inline copy.
export const INVALID_VERSION_MESSAGE = 'Сервер вернул документ без корректной версии.'

interface DocumentWire {
  document_id: string
  status: string
  content: string
  version: number
}

// The single fail-closed guard, applied wherever a wire version becomes a token a PUT will carry
// (create, get, put) — including the 409 refetch, which flows through getDocument. `Number.isFinite`
// rejects undefined, null, and unparseable strings ("abc") as well as NaN/Infinity without coercing,
// so every non-finite shape fails closed here rather than being re-PUT unguarded.
function parseVersion(raw: unknown): number {
  if (!Number.isFinite(raw)) {
    throw new Error(INVALID_VERSION_MESSAGE)
  }
  return raw as number
}

export interface CreateDocumentResult {
  documentId: string
  status: string
  version: number
}

// `version` is REQUIRED, not optional, and that is the point: it is the optimistic-concurrency
// token the next PUT must carry (documents_create.yaml). An optional field would let a caller
// fall back to a guess — which is exactly the bug this replaced, where the create response's
// version was parsed away and `useState(1)` shipped in its place, earning a 409 that blamed a
// concurrent save that never happened.
//
// `idempotencyKey` is REQUIRED for the same reason. Minting it inside this function made the
// spec's 200-replay branch unreachable by construction: every call sent a fresh key, so no
// replay could ever be recognised. The caller owns it because only the caller knows what "the
// same logical create" means — see useDocumentInit, where one mount must survive StrictMode's
// double-invoked effect as ONE document.
export async function createDocument(
  documentType: DocumentType,
  idempotencyKey: string,
): Promise<CreateDocumentResult> {
  const data = await send<DocumentWire>(
    '/api/v1/documents',
    {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      // Translated at the boundary: the wire wants Cyrillic, the app's DocumentType is Latin.
      // Sending the Latin id is a 422 INVALID_DOCUMENT_TYPE — measured, not assumed.
      //
      // `content` is deliberately absent, though the backend turned out to IGNORE server-owned
      // fields rather than reject them (so sending it was never the 422 the spec threatened).
      // Omitting it is still right: the request should say what it means, and a field the
      // server discards is a claim about ownership that is not ours to make.
      body: { document_type: WIRE_DOCUMENT_TYPE[documentType] },
    },
    'Не удалось создать документ',
  )
  return { documentId: data.document_id, status: data.status, version: parseVersion(data.version) }
}

export interface SaveDocumentResult {
  status: string
  version: number
  // The SANITIZED content, as persisted — not the string that was sent. Measured 2026-07-17:
  //   sent  <p>Привет</p><script>alert(1)</script><br />
  //   got   <p>Привет</p><br>
  // The server strips <script> with its contents and normalises void tags. Whoever holds the
  // editor state must adopt this, or the editor keeps rendering markup the server does not
  // have and re-sends it on every subsequent save.
  content: string
}

async function putDocument(
  documentId: string,
  content: string,
  version: number,
): Promise<SaveDocumentResult> {
  const data = await send<DocumentWire>(
    `/api/v1/documents/${documentId}`,
    {
      method: 'PUT',
      body: { content, version },
    },
    'Не удалось сохранить документ',
  )
  return { status: data.status, version: parseVersion(data.version), content: data.content }
}

// On 409 the backend prescribes the recovery itself ("Refetch and retry"), so it is encoded
// here rather than pushed onto every caller — the same reason authorizedRequest owns the 401
// renewal. Measured 2026-07-17: a stale version with DIFFERENT content returns
// 409 VERSION_CONFLICT and the stored document is untouched; a stale version with IDENTICAL
// content returns 200 as an idempotent replay, so this path only runs on a real divergence.
//
// EXACTLY ONE retry. A second 409 means the version we just fetched went stale within one
// round trip, which a loop would not fix — it would just hammer the endpoint.
//
// TRADE-OFF, stated because it is a product decision and not obviously right: the retry sends
// OUR content against the refetched version, i.e. last-writer-wins — the other save's text is
// overwritten. Documents are single-owner (no sharing exists), so the realistic source of a
// conflict is the same person in a second tab, and silently discarding one tab's paragraph is
// still a real loss. The alternative is surfacing the conflict and letting them choose, which
// needs UI this story does not have. Revisit when it does.
export async function saveDocument(
  documentId: string,
  content: string,
  version: number,
): Promise<SaveDocumentResult> {
  try {
    return await putDocument(documentId, content, version)
  } catch (error) {
    if (!(error instanceof VersionConflictError)) {
      throw error
    }
    const current = await getDocument(documentId)
    return await putDocument(documentId, content, current.version)
  }
}

export interface GetDocumentResult {
  documentId: string
  status: string
  content: string
  version: number
}

export async function getDocument(documentId: string): Promise<GetDocumentResult> {
  const data = await send<DocumentWire>(
    `/api/v1/documents/${documentId}`,
    {},
    'Не удалось загрузить документ',
  )
  return {
    documentId: data.document_id,
    status: data.status,
    content: data.content,
    version: parseVersion(data.version),
  }
}
