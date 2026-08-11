import { describe, expect, it } from 'vitest'
import { DocumentNotFoundError, loadEditorDocument } from '../editorDocumentApi'
import { SessionExpiredError } from '../../../auth/api/authorizedRequest'
import { rejectionOf } from '../../../../test/rejectionOf'
import {
  DOCUMENT_URL,
  INTERNAL_ERROR_MESSAGE,
  INTERNAL_ERROR_RESPONSE,
  NOT_FOUND_MESSAGE,
  NOT_FOUND_RESPONSE,
  okJson,
  REFRESH_URL,
  SESSION_EXPIRED_MESSAGE,
  signedInSessionAroundEach,
  UNAUTHORIZED_RESPONSE,
  expectErrorIdentity,
  requestedUrls,
  stubFetch,
} from './aiChatApiFixtures'

// DESIGN DECISION, recorded here because the previous /refactor pass deferred it to this work
// unit and the tests below only make sense once it is settled.
//
// `loadEditorDocument`/`EditorDocument` and `getDocument`/`GetDocumentResult` (generation/api/
// documentApi.ts) are the same GET on the same endpoint. Two options were on the table:
//
//   (a) test-drive `loadEditorDocument` as its own fetch that adds a 404 branch, or
//   (b) drive the 404 → DocumentNotFoundError mapping into the shared `send`, and let
//       `loadEditorDocument` be a thin wrapper over the ONE existing loader.
//
// (b), for a reason that is structural rather than aesthetic: `send` already FLATTENS every
// non-401/409 refusal into `new Error(describeFailure(...))`. By the time `getDocument` returns
// control, a 404 and a 500 are the same generic Error with different text — so a wrapper CANNOT
// recover the distinction, and (a) would have had to bypass `send` and re-implement the token
// attach, the 401 renew-and-replay, and the refusal-describing. That is a second copy of exactly
// the carve-out `send.ts`'s own header says a second copy gets wrong.
//
// So: the 404 branch belongs beside the 409 branch, keyed on the CODE and not the bare status,
// for the same reason the 409 branch is (`send.ts` lines 56-62) — and `endpoints.md` earns it:
// "All seven endpoints share one 404 body", `{"error_code": "NOT_FOUND", "message": ...}`.
// `DocumentNotFoundError` therefore lands in `shared/api/send.ts` next to VersionConflictError
// and SessionExpiredError, and `editorDocumentApi` re-exports it — the import path the hook and
// the component tests already use stays valid.
//
// ONE error type covers both halves of the scenario's Given. An absent document and another
// account's document are byte-identical from the client (endpoints.md: "Absent document, foreign
// document ... are byte-identical ... Never 403"), so there is nothing here to tell apart.
// TDD RED (Story 19, Frontend Scenario 0.1). Verified failing 2026-08-09: all 5 cases fail on
// `Error: Not implemented: loadEditorDocument(doc-1)` — the stub throws unconditionally, so the
// happy path rejects instead of resolving, the two 404 cases get a plain Error where
// DocumentNotFoundError is required, the 401 case gets one where SessionExpiredError is, and the
// 500 case gets "Not implemented: …" where the described refusal text is. `describe.skip` rather
// than five `it.skip`s: one function under test, one marker (the adapter-class convention).
// Unskipped in green-frontend-api.
describe('editorDocumentApi loadEditorDocument', () => {
  // Stores the session every case needs and tears down `stubFetch`'s global. Rationale beside it.
  signedInSessionAroundEach()

  it('loads the document behind /documents/{id} and renames the wire fields', async () => {
    const fetchMock = stubFetch(
      okJson({ document_id: 'doc-1', status: 'draft', content: '<p>Привет</p>', version: 4 }),
    )

    // `status` is deliberately absent from the result: the editor renders content and sends
    // `version` back on save, and nothing in this feature branches on the document's status.
    // `toEqual` on the whole object rather than per-field: it also fails if `status` leaks
    // through, which a per-field check would not.
    await expect(loadEditorDocument('doc-1')).resolves.toEqual({
      documentId: 'doc-1',
      content: '<p>Привет</p>',
      version: 4,
    })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe(DOCUMENT_URL)
    // A read, and only a read. Without these the same test passes for a POST that happens to
    // return the document, which is the shape that creates one on every page open.
    expect(init.method).toBe('GET')
    expect(init.body).toBeUndefined()
    expect(init.headers.Authorization).toBe('Bearer access-1')
  })

  // The scenario's Given, both halves at once. A green that produced the right sentence with the
  // wrong class would still route the user to the generic failure screen — follow-up (r) unfixed.
  it('maps the shared 404 body onto DocumentNotFoundError', async () => {
    const fetchMock = stubFetch(NOT_FOUND_RESPONSE)

    const error = await rejectionOf(loadEditorDocument('doc-1'))
    expectErrorIdentity(error, DocumentNotFoundError, 'DocumentNotFoundError', NOT_FOUND_MESSAGE)
    // Exactly one call: a 404 is a statement about the document, not about the session, so it
    // must not send the request through `authorizedRequest`'s renew-and-replay.
    expect(requestedUrls(fetchMock)).toEqual([DOCUMENT_URL])
  })

  it('rejects a foreign account document — the same 404 — with the same error type', async () => {
    const fetchMock = stubFetch(NOT_FOUND_RESPONSE)

    const error = await rejectionOf(loadEditorDocument('doc-owned-by-someone-else'))
    expectErrorIdentity(error, DocumentNotFoundError, 'DocumentNotFoundError', NOT_FOUND_MESSAGE)
    // The id reaches the URL: without this the case is indistinguishable from the one above and
    // would pass for an implementation that ignores its argument.
    expect(requestedUrls(fetchMock)).toEqual(['/api/v1/documents/doc-owned-by-someone-else'])
  })

  // Review follow-up (n): an expired session must NOT arrive as DocumentNotFoundError. It is not
  // a statement about the document at all — the document may well exist — and folding it in would
  // tell a signed-out user their work is gone and offer to re-create it. Naming SessionExpiredError
  // positively is what fails an implementation that maps every rejection to DocumentNotFoundError;
  // a bare `not.toBeInstanceOf(DocumentNotFoundError)` would add nothing and is left out rather
  // than kept as decoration.
  //
  // Two 401s: the first triggers `authorizedRequest`'s renew-and-replay, the refresh call is the
  // second, and its failure ends the session. That is the only path that reaches the caller as
  // SessionExpiredError, so the shortcut of clearing the session in setup would test the no-token
  // guard instead of the refusal this follow-up is about — and the call list below is what pins
  // that the path actually taken was that one.
  it('lets SessionExpiredError through instead of folding it into not-found', async () => {
    const fetchMock = stubFetch(UNAUTHORIZED_RESPONSE, UNAUTHORIZED_RESPONSE)

    const error = await rejectionOf(loadEditorDocument('doc-1'))
    expectErrorIdentity(error, SessionExpiredError, 'SessionExpiredError', SESSION_EXPIRED_MESSAGE)
    expect(requestedUrls(fetchMock)).toEqual([DOCUMENT_URL, REFRESH_URL])
  })

  // The other side of the same line: everything that is NOT the 404 keeps the describing `send`
  // already does, so the failure screen says the load broke rather than that the document is
  // gone. A bare `catch → not found` fails HERE — on `name` being the plain 'Error' and on the
  // message being the server's, both of which DocumentNotFoundError's fixed Russian sentence
  // contradicts. Pinning `name` to 'Error' is stronger than `not.toBeInstanceOf(
  // DocumentNotFoundError)`: it also rules out SessionExpiredError, VersionConflictError and any
  // other subclass a green might reach for.
  it('keeps a 500 as a described generic failure, not not-found', async () => {
    const fetchMock = stubFetch(INTERNAL_ERROR_RESPONSE)

    const error = await rejectionOf(loadEditorDocument('doc-1'))
    expectErrorIdentity(error, Error, 'Error', INTERNAL_ERROR_MESSAGE)
    // A 500 is not a session problem either — no renew, no replay.
    expect(requestedUrls(fetchMock)).toEqual([DOCUMENT_URL])
  })
})
