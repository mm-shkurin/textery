import { expect } from 'vitest'
import type { MockedFunction } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { useEditorDocument, type EditorDocumentState } from '../useEditorDocument'
import type { loadEditorDocument, EditorDocument } from '../../api/editorDocumentApi'

// Shared setup for the two cases that pin `useEditorDocument`'s per-request token guard: one for
// its `.then` arm (`useEditorDocument.supersededResponse.test.tsx`) and one for its `.catch` arm
// (`useEditorDocument.supersededRejection.test.tsx`). Both need the identical ping-pong premise and
// differ only in how the superseded request settles, so the premise lives here and each case file
// holds just its own settlement and conclusion. The files are separate because the two together
// exceeded the 200-line cap; `vi.mock` is hoisted per test file, so each still declares its own and
// passes the resulting mock in.

export const DOCUMENT_ID = '7a3d5e19-2c64-4b08-8f52-91ad3e7c0b6f'
export const OTHER_DOCUMENT_ID = 'c81b0f4a-6d27-4e93-a05c-3fb27de41859'

// Same id, two different server states — the point of both cases. Only `version` differing would
// do, but the content differs too so the failure output names which response won without arithmetic.
export const SUPERSEDED_DOCUMENT: EditorDocument = {
  documentId: DOCUMENT_ID,
  content: '<p>Введение к докладу</p>',
  version: 3,
}
export const FRESH_DOCUMENT: EditorDocument = {
  documentId: DOCUMENT_ID,
  content: '<p>Введение к докладу, переписанное ИИ</p>',
  version: 9,
}
export const OTHER_DOCUMENT: EditorDocument = {
  documentId: OTHER_DOCUMENT_ID,
  content: '<p>Тезисы второго доклада</p>',
  version: 1,
}

// Typed as the hook's own state union, not left inferred: inferred, `status` widens to `string` and
// a typo in the literal ('redy') would be a compile-time no-op that both cases then assert in
// lockstep, failing with a diff about the wrong thing. The annotation makes the expectation
// answerable to the production type it claims to describe.
export const READY_ON_FRESH: EditorDocumentState = { status: 'ready', document: FRESH_DOCUMENT }

// The ping-pong, as a call list. Asserted twice per case — once as the premise (two outstanding
// requests for A exist at all) and once as the conclusion (the superseded request was dropped, not
// recovered from). One constant so the two can never drift into asserting different things.
const PING_PONG_CALLS = [[DOCUMENT_ID], [OTHER_DOCUMENT_ID], [DOCUMENT_ID]]

type LoadMock = MockedFunction<typeof loadEditorDocument>
type Resolvers = ((document: EditorDocument) => void)[]
type HookResult = { readonly current: EditorDocumentState }

// One deferred per call, in call order: the settlement order is the whole experiment, so it must be
// driven by the test rather than by whatever order the mock happens to settle in. Both levers are
// captured per call — which of the two a case pulls is exactly what separates the `.then` arm from
// the `.catch` arm of the same guard.
function deferredLoads(loadEditorDocumentMock: LoadMock) {
  const resolvers: Resolvers = []
  const rejecters: ((error: unknown) => void)[] = []
  loadEditorDocumentMock.mockImplementation(
    () =>
      new Promise<EditorDocument>((resolve, reject) => {
        resolvers.push(resolve)
        rejecters.push(reject)
      }),
  )
  return { resolvers, rejecters }
}

// Renders the hook and walks it A → B → A with nothing settled, leaving two outstanding requests
// for A. Everything asserted here is the premise both cases stand on, not their conclusion.
export function startPingPong(loadEditorDocumentMock: LoadMock) {
  const { resolvers, rejecters } = deferredLoads(loadEditorDocumentMock)

  const { result, rerender } = renderHook(
    ({ documentId }: { documentId: string }) => useEditorDocument(documentId),
    { initialProps: { documentId: DOCUMENT_ID } },
  )

  // Each leg resets to `loading`, asserted synchronously before the next one. Without this the
  // final assertion would still pass against a hook that had stopped clearing the previous document
  // on an id change — showing one document's text under another's id.
  rerender({ documentId: OTHER_DOCUMENT_ID })
  expect(result.current).toStrictEqual({ status: 'loading' })
  rerender({ documentId: DOCUMENT_ID })
  expect(result.current).toStrictEqual({ status: 'loading' })

  // Three requests, in this order — asserted before anything settles, because the ping-pong is the
  // premise: if the hook ever stopped re-fetching the returned-to id there would be only one
  // outstanding request for it and nothing in either case could fail.
  expectPingPongNotRepeated(loadEditorDocumentMock)
  // One captured lever per call, both kinds. `mock.calls` above proves the hook asked three times,
  // not that the fixture handed back three levers — and without this an absent `resolvers[2]` or
  // `rejecters[0]` would kill the case with a TypeError instead of a readable diff.
  expect(resolvers).toHaveLength(3)
  expect(rejecters).toHaveLength(3)

  return { result, resolvers, rejecters }
}

// The SECOND request for A answers first and succeeds — the good state that each case's late
// settlement must not be allowed to destroy. Still premise, not conclusion: it is identical in both
// cases, and living here means the two can never drift into standing on different good states.
export async function settleNewestRequestFirst(result: HookResult, resolvers: Resolvers) {
  await act(async () => {
    resolvers[2](FRESH_DOCUMENT)
  })
  await waitFor(() => {
    expect(result.current).toStrictEqual(READY_ON_FRESH)
  })
}

// No recovery re-fetch: a green that noticed the mismatch and re-issued a fetch for A would land on
// FRESH_DOCUMENT too and satisfy the state assertion, while turning every ping-pong into an extra
// round trip. The superseded request must be DROPPED, not recovered from.
export function expectPingPongNotRepeated(loadEditorDocumentMock: LoadMock) {
  // `toStrictEqual`, matching every state assertion in both cases: `toEqual` treats a key holding
  // `undefined` as absent, so a hook that grew a second parameter and passed it as `undefined`
  // (a signal, an abort handle) would keep passing while the call list had silently changed shape.
  expect(loadEditorDocumentMock.mock.calls).toStrictEqual(PING_PONG_CALLS)
}
