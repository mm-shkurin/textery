import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { useEditorDocument } from '../useEditorDocument'
import { loadEditorDocument, type EditorDocument } from '../../api/editorDocumentApi'

// Story 19, Frontend Scenario 0.1 — the re-scoped coverage step "a superseded response for the
// SAME id loses" (follow-up (aj) in progress-frontend.md).
//
// THE ORIGINAL WORDING DESCRIBED A CASE ALREADY HANDLED. "A stale response for an OLD id is
// ignored" is what `if (requestedIdRef.current !== documentId) return` does: while the user sits on
// B, A's response carries an id that is no longer the requested one and is dropped. That arm is
// worth covering, but it is not where the hook is wrong.
//
// WHAT IS ACTUALLY BROKEN. `requestedIdRef` stores an *id*, not a *request*. Route ping-pong
// A → B → A issues two fetches for A, and by the time A's FIRST response resolves the ref has been
// set back to `A` — so the superseded response passes the identity check and calls setState. The
// user is shown the document as it was before the round trip, and with it a stale `version`, which
// `editorDocumentApi.ts` documents as travelling back to the server on the next save: a lost-update
// write built out of a response the hook itself already superseded. Two outstanding requests for
// one id cannot be told apart by that id; only a per-request token can.
//
// This is a real defect on main, not a mutation exercise — the test below fails against the
// unmodified hook.
//
// WHY NO StrictMode WRAPPER, UNLIKE THE SIBLING FILE. `useEditorDocument.strictMode.test.tsx` is
// *about* the double-invoke: its subject is how many requests are issued, and that only becomes
// observable when React runs the effect twice. Here the subject is which of two responses wins, and
// the dedupe guard already collapses each double-invoke to one fetch — so StrictMode would leave
// the call list identical (A, B, A) while doubling every render in the failure output. Worse, it
// would imply the defect is a dev-mode artefact. It is not: the three fetches come from three
// distinct ids being requested, which is plain user navigation in production.

const DOCUMENT_ID = '7a3d5e19-2c64-4b08-8f52-91ad3e7c0b6f'
const OTHER_DOCUMENT_ID = 'c81b0f4a-6d27-4e93-a05c-3fb27de41859'

// Same id, two different server states — the point of the case. Only `version` differing would do,
// but the content differs too so the failure output names which response won without arithmetic.
const SUPERSEDED_DOCUMENT: EditorDocument = {
  documentId: DOCUMENT_ID,
  content: '<p>Введение к докладу</p>',
  version: 3,
}
const FRESH_DOCUMENT: EditorDocument = {
  documentId: DOCUMENT_ID,
  content: '<p>Введение к докладу, переписанное ИИ</p>',
  version: 9,
}
const OTHER_DOCUMENT: EditorDocument = {
  documentId: OTHER_DOCUMENT_ID,
  content: '<p>Тезисы второго доклада</p>',
  version: 1,
}

vi.mock('../../api/editorDocumentApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/editorDocumentApi')>()
  return { ...actual, loadEditorDocument: vi.fn() }
})

const loadEditorDocumentMock = vi.mocked(loadEditorDocument)

// One deferred per call, in call order: the resolution order is the whole experiment, so it must be
// driven by the test rather than by whatever order the mock happens to settle in.
function deferredLoads() {
  const resolvers: ((document: EditorDocument) => void)[] = []
  loadEditorDocumentMock.mockImplementation(
    () => new Promise<EditorDocument>((resolve) => resolvers.push(resolve)),
  )
  return resolvers
}

describe('useEditorDocument with two outstanding requests for the same document', () => {
  beforeEach(() => {
    loadEditorDocumentMock.mockReset()
  })

  // RED: verified failing against unmodified main —
  // AssertionError: expected { status: 'ready', document: { content: '<p>Введение к докладу</p>',
  // version: 3 } } to deeply equal { …, version: 9 }. The superseded first response for A wins
  // because `requestedIdRef.current` is back to A when it resolves. `green-frontend` adds a
  // per-request token beside the id key and un-skips this.
  it.skip('keeps the newest response when the superseded request for the same id resolves last', async () => {
    const resolvers = deferredLoads()

    const { result, rerender } = renderHook(
      ({ documentId }: { documentId: string }) => useEditorDocument(documentId),
      { initialProps: { documentId: DOCUMENT_ID } },
    )

    // Each leg of the ping-pong resets to `loading`, asserted synchronously before the next one.
    // Without this the final assertion would still pass against a hook that had stopped clearing
    // the previous document on an id change — showing one document's text under another's id.
    rerender({ documentId: OTHER_DOCUMENT_ID })
    expect(result.current).toStrictEqual({ status: 'loading' })
    rerender({ documentId: DOCUMENT_ID })
    expect(result.current).toStrictEqual({ status: 'loading' })

    // Three requests, in this order — asserted before any of them resolves, because the ping-pong
    // is the premise of the case: if the hook ever stopped re-fetching the returned-to id there
    // would be only one outstanding request for it and nothing below could fail.
    expect(loadEditorDocumentMock.mock.calls).toEqual([
      [DOCUMENT_ID],
      [OTHER_DOCUMENT_ID],
      [DOCUMENT_ID],
    ])
    // One captured resolver per call. Pins the fixture itself: `mock.calls` above proves the hook
    // asked three times, not that `deferredLoads` handed back three levers — and without this an
    // absent `resolvers[2]` would kill the test with a TypeError instead of a readable diff.
    expect(resolvers).toHaveLength(3)

    // The second request for A answers first.
    await act(async () => {
      resolvers[2](FRESH_DOCUMENT)
    })
    await waitFor(() => {
      expect(result.current).toStrictEqual({ status: 'ready', document: FRESH_DOCUMENT })
    })

    // Then B's response, from the id the user has already left. Resolved in its OWN act and
    // asserted on its own, so the pre-existing old-id guard is genuinely pinned: flushed together
    // with A's response it would have been dropped by microtask ordering rather than by the guard,
    // and nothing here would have failed if the guard were deleted.
    await act(async () => {
      resolvers[1](OTHER_DOCUMENT)
    })
    expect(result.current).toStrictEqual({ status: 'ready', document: FRESH_DOCUMENT })

    // …and only now the first, superseded request for A comes back.
    await act(async () => {
      resolvers[0](SUPERSEDED_DOCUMENT)
    })

    // The whole state, not `document.version` alone: a hook that dropped the superseded response by
    // resetting to `{ status: 'loading' }` would also be wrong, and a version-only assertion would
    // not see it. `toStrictEqual` throughout, not `toEqual`, because `toEqual` treats a key holding
    // `undefined` as absent — a green that widened the union to carry an `error?` alongside a
    // stale-but-present document would satisfy `toEqual` and be exactly the bug this file is about.
    expect(result.current).toStrictEqual({ status: 'ready', document: FRESH_DOCUMENT })

    // Still three calls: the superseded response must be DROPPED, not recovered from. A green that
    // noticed the mismatch and re-issued a fetch for A would land on FRESH_DOCUMENT too and satisfy
    // the state assertion above, while turning every route ping-pong into an extra round trip.
    expect(loadEditorDocumentMock.mock.calls).toEqual([
      [DOCUMENT_ID],
      [OTHER_DOCUMENT_ID],
      [DOCUMENT_ID],
    ])
  })
})
