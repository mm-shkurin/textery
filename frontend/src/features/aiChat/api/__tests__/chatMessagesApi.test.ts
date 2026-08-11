import { describe, expect, expectTypeOf, it } from 'vitest'
import { loadChatMessages, type ChatMessage, type ChatMessagePage } from '../chatMessagesApi'
import type { ChatMessage as PanelChatMessage } from '../../components/AiChatPanel'
import { DocumentNotFoundError } from '../../../../shared/api/send'
import { SessionExpiredError } from '../../../auth/api/authorizedRequest'
import { rejectionOf } from '../../../../test/rejectionOf'
import {
  expectErrorIdentity,
  MESSAGES_URL,
  NOT_FOUND_RESPONSE,
  NOT_FOUND_WIRE_MESSAGE,
  okJson,
  REFRESH_URL,
  requestedUrls,
  SESSION_EXPIRED_MESSAGE,
  signedInSessionAroundEach,
  stubFetch,
  UNAUTHORIZED_RESPONSE,
} from './aiChatApiFixtures'

// Story 19, Frontend Scenario 1.1 — the CLIENT half of "the chat panel renders with an empty
// history". `documents_messages_list.yaml` is the contract; 1.2 owns restored conversations,
// ordering and paging, and 1.3 owns the failure SCREEN. What is settled here is what the client
// hands those scenarios.
//
// DESIGN DECISION, made explicitly rather than inherited: this call does NOT pass
// `{ notFound: true }`. `send.ts:45-54` made that mapping opt-in per call precisely because
// `error_code: 'NOT_FOUND'` is shared by all seven endpoints, and this is a caller that must
// decline it. Two reasons. (1) The page reads the DOCUMENT too, through `loadEditorDocument`,
// which does opt in — that read is the authoritative one and already renders the not-found
// blocker, so a second typed 404 races it to say the same thing about the same fact. (2) A 404
// reaching the history read while the document loaded fine is not "your document is gone"; it is
// the history endpoint failing, which is 1.3's separate panel. `DocumentNotFoundError` here would
// blank the whole editor over a broken sidebar.
//
// That decision is also what finally covers the opt-in guard itself — follow-up (x): there is no
// `send` test file at all, and the one case that looks like coverage
// (`generation/api/__tests__/documentApi.test.ts:180`) stubs a 404 with NO `error_code`, so the
// branch cannot fire for it even if `refusals` were deleted outright. The 404 case below is the
// first anywhere that meets `{status: 404, error_code: 'NOT_FOUND'}` from a caller passing no
// refusals — deleting the `refusals` parameter turns it red.
const FALLBACK = 'Не удалось загрузить историю чата'

const MESSAGE_WIRE = {
  message_id: 'm-1',
  role: 'user',
  text: 'Сократи введение',
  created_at: '2026-08-11T09:12:00+03:00',
  edit_id: 'e-1',
}
const SECOND_MESSAGE_WIRE = {
  ...MESSAGE_WIRE,
  message_id: 'm-2',
  role: 'assistant',
  text: 'Готово',
}

// TDD RED (Story 19, Frontend Scenario 1.1). `chatMessagesApi.ts` is a stub that throws
// `Not implemented: loadChatMessages(<id>)` unconditionally, so every case below fails on it: the
// two mapping cases as a rejection where a resolution is required, and every refusal case on the
// asserted message (and, for the session case, on the class). Verified failing 2026-08-11, 8 of 8,
// with exactly those messages. `describe.skip` rather than eight
// `it.skip`s: one function under test, one marker — the convention this feature's two sibling API
// test files already follow. Unskipped in `green-frontend-api`.
describe.skip('chatMessagesApi loadChatMessages', () => {
  // Stores the session every case needs and tears down `stubFetch`'s global. Rationale beside it.
  signedInSessionAroundEach()

  it('reads the document history and reports an empty conversation as an empty page', async () => {
    const fetchMock = stubFetch(okJson({ items: [] }))

    // `nextCursor: null` from an ABSENT key, not merely from a null one: the schema says
    // "Absent or null on the last page", and `toStrictEqual` (unlike `toEqual`) refuses the
    // `undefined` a pass-through rename would leave there. An `undefined` cursor is the value a
    // later `if (page.nextCursor)` reads correctly and a `'cursor' in page` reads wrongly.
    await expect(loadChatMessages('doc-1')).resolves.toStrictEqual({
      messages: [],
      nextCursor: null,
    })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe(MESSAGES_URL)
    // A read, and only a read, pinned as ONE CLOSED object — per-field checks say nothing about
    // keys they do not name, so a green adding a body or a second header passes them all. `init`
    // is exhaustively known: `performRequest` passes exactly `{method, signal, headers, body}`.
    // `body: undefined` under `toStrictEqual` is what fails a green that POSTs to a history read.
    expect(init).toStrictEqual({
      method: 'GET',
      signal: expect.any(AbortSignal),
      headers: { Authorization: 'Bearer access-1' },
      body: undefined,
    })
    // The signature, enforced rather than narrated — and the mirror image of `loadEditQuota`'s
    // zero-parameter gate. This history IS document-scoped, so an account-scoped signature that
    // dropped the id would read one conversation for every document. `toEqualTypeOf` is exact in
    // both directions, so an optional or defaulted parameter fails it where `.length` would not.
    expectTypeOf(loadChatMessages).toEqualTypeOf<(documentId: string) => Promise<ChatMessagePage>>()
  })

  // The other half of the mapping, and NOT optional decoration: without it the case above is
  // satisfied by `async () => ({ messages: [], nextCursor: null })` — a client that reports every
  // conversation empty. That is follow-up (bf) one layer down, where 1.1's pristine document
  // cannot tell a conditional empty state from an unconditional one.
  it('renames the wire fields, drops what no view reads, and carries the cursor', async () => {
    stubFetch(okJson({ items: [MESSAGE_WIRE, SECOND_MESSAGE_WIRE], next_cursor: 'c-2' }))

    // Whole-object `toStrictEqual`, so it also fails if `created_at`/`edit_id` leak through
    // unrenamed beside the mapped fields — which a per-field check would not. They are dropped for
    // the reason `editorDocumentApi` drops `status`: no view reads them, and 1.2 (which owns
    // ordering and the per-side split) is where a timestamp earns its way back in.
    await expect(loadChatMessages('doc-1')).resolves.toStrictEqual({
      messages: [
        { messageId: 'm-1', role: 'user', text: 'Сократи введение' },
        { messageId: 'm-2', role: 'assistant', text: 'Готово' },
      ],
      nextCursor: 'c-2',
    })

    // A COMPILE-TIME gate against the second copy of this type. `AiChatPanel` already exports its
    // own `ChatMessage` (shipped by `green-frontend` before any read existed) and the api layer is
    // where the wire rename happens, so there are now two declarations of one concept. TypeScript
    // is structural, so they cannot diverge by `instanceof` — they diverge silently, by one
    // growing a field. This fails `tsc` the moment they do; consolidating them is green's or
    // `/refactor`'s, and moving a shipped production type is not a RED phase's licence to take.
    expectTypeOf<ChatMessage>().toEqualTypeOf<PanelChatMessage>()
  })

  // SILENCE MUST REFUSE, and this is the client-layer half of follow-up (bp): `AiChatPanel`
  // branches on `messages.length === 0` alone, so "empty" and "unknown" are already one value in
  // the component. `performRequest` ends with `res.json().catch(() => ({}))`, so a 204, an empty
  // 200 and a proxy's HTML page served with a 200 all arrive here as `{}` — and a green written as
  // `body.items ?? []` answers "this document has never been edited" for an endpoint that said
  // nothing. The user then retypes an instruction that already landed, burning a quota unit and
  // stacking a second AI revision. A rejection is the only value 1.3 can build its panel on.
  //
  // The CURSOR row is third because `nextCursor: string | null` is a promise this module's own
  // return type makes, and nothing else in the file makes the wire keep it. A green written as
  // `next_cursor ?? null` satisfies every other case here while typing an arbitrary value `string`
  // by declaration alone — and scenario 1.2, the first to send the cursor back, would interpolate
  // `[object Object]` into a query string and get a 422 for a page the user can see. Absent and
  // null are the contract's two "last page" spellings and stay values; anything else is the
  // endpoint failing to state a page, which is this table's subject.
  it.each([
    ['an empty body', {}],
    ['items that are not a list', { items: 'nope' }],
    ['a cursor that is neither absent nor a string', { items: [], next_cursor: 42 }],
  ])('refuses a 200 that does not carry a page: %s', async (_case, body) => {
    stubFetch(okJson(body))

    const error = await rejectionOf(loadChatMessages('doc-1'))
    expectErrorIdentity(error, Error, 'Error', FALLBACK)
  })

  // Per-ROW guards, for the same reason one level down. An unchecked rename yields
  // `{messageId: undefined, text: undefined}`, which React renders as an empty `<p>` keyed
  // `undefined` — follow-up (br)'s dropped-row bug, arriving from the wire rather than from a
  // fixture. `role` is checked against its two enum values and not merely for being a string: it
  // is what scenario 1.2 splits the conversation on, and a third value would silently pick a side.
  it.each([
    ['a message with no text', { message_id: 'm-1', role: 'user' }],
    ['a role outside the enum', { ...MESSAGE_WIRE, role: 'system' }],
  ])('refuses a page whose message the wire did not fully state: %s', async (_case, message) => {
    stubFetch(okJson({ items: [message] }))

    const error = await rejectionOf(loadChatMessages('doc-1'))
    expectErrorIdentity(error, Error, 'Error', FALLBACK)
  })

  // FOLLOW-UP (x)'s closer, and the decision at the top of this file made executable. Pinning
  // `name` to 'Error' is what rules out `DocumentNotFoundError` — asserted a second time below
  // because this one case carries the whole opt-in guard and a reader must not have to derive its
  // subject from a `name` string. The MESSAGE is the server's own sentence surviving
  // `describeFailure`, which additionally fails a green that raises the class and lets its fixed
  // Russian text through. Delete `refusals` from `send` and this case is the only thing that
  // reddens in the suite.
  it('keeps the shared 404 as a described generic failure, not DocumentNotFoundError', async () => {
    const fetchMock = stubFetch(NOT_FOUND_RESPONSE)

    const error = await rejectionOf(loadChatMessages('doc-gone'))
    expectErrorIdentity(error, Error, 'Error', NOT_FOUND_WIRE_MESSAGE)
    expect(error).not.toBeInstanceOf(DocumentNotFoundError)
    // The id reaches the wire INTERPOLATED: every other case sends 'doc-1', which a client with the
    // path hardcoded would satisfy. Also: a 404 is a statement about the request, not the session,
    // so no renew and no replay.
    expect(requestedUrls(fetchMock)).toStrictEqual(['/api/v1/documents/doc-gone/messages'])
  })

  // An expired session is not a statement about the history — folding it into the generic failure
  // would show 1.3's "the conversation could not be loaded" to a user who is simply signed out.
  // Two 401s: the first triggers `authorizedRequest`'s renew-and-replay, the second is the refresh
  // failing, which is the only path that reaches a caller as SessionExpiredError — and the call
  // list is what pins that the path taken was that one.
  it('lets SessionExpiredError through instead of describing it as a load failure', async () => {
    const fetchMock = stubFetch(UNAUTHORIZED_RESPONSE, UNAUTHORIZED_RESPONSE)

    const error = await rejectionOf(loadChatMessages('doc-1'))
    expectErrorIdentity(error, SessionExpiredError, 'SessionExpiredError', SESSION_EXPIRED_MESSAGE)
    expect(requestedUrls(fetchMock)).toStrictEqual([MESSAGES_URL, REFRESH_URL])
  })
})
