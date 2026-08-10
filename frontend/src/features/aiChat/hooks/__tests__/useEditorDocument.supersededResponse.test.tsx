import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act } from '@testing-library/react'
import { loadEditorDocument } from '../../api/editorDocumentApi'
import {
  OTHER_DOCUMENT,
  READY_ON_FRESH,
  SUPERSEDED_DOCUMENT,
  expectPingPongNotRepeated,
  settleNewestRequestFirst,
  startPingPong,
} from './supersededRequestFixture'

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
//
// The `.catch` twin of this case lives in `useEditorDocument.supersededRejection.test.tsx`; the
// shared ping-pong premise lives in `supersededRequestFixture.ts`.

vi.mock('../../api/editorDocumentApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/editorDocumentApi')>()
  return { ...actual, loadEditorDocument: vi.fn() }
})

const loadEditorDocumentMock = vi.mocked(loadEditorDocument)

describe('useEditorDocument with two outstanding requests for the same document', () => {
  beforeEach(() => {
    loadEditorDocumentMock.mockReset()
  })

  // RED: verified failing against unmodified main —
  // AssertionError: expected { status: 'ready', document: { content: '<p>Введение к докладу</p>',
  // version: 3 } } to deeply equal { …, version: 9 }. The superseded first response for A won
  // because `requestedIdRef.current` was back to A when it resolved. Green has since landed the
  // per-request token beside the id key, so this now passes; delete the `.then` token guard and
  // the failure above returns.
  it('keeps the newest response when the superseded request for the same id resolves last', async () => {
    const { result, resolvers } = startPingPong(loadEditorDocumentMock)
    await settleNewestRequestFirst(result, resolvers)

    // Then B's response, from the id the user has already left. Resolved in its OWN act and
    // asserted on its own, so the pre-existing old-id guard is genuinely pinned: flushed together
    // with A's response it would have been dropped by microtask ordering rather than by the guard,
    // and nothing here would have failed if the guard were deleted.
    await act(async () => {
      resolvers[1](OTHER_DOCUMENT)
    })
    expect(result.current).toStrictEqual(READY_ON_FRESH)

    // …and only now the first, superseded request for A comes back.
    await act(async () => {
      resolvers[0](SUPERSEDED_DOCUMENT)
    })

    // The whole state, not `document.version` alone: a hook that dropped the superseded response by
    // resetting to `{ status: 'loading' }` would also be wrong, and a version-only assertion would
    // not see it. `toStrictEqual` throughout, not `toEqual`, because `toEqual` treats a key holding
    // `undefined` as absent — a green that widened the union to carry an `error?` alongside a
    // stale-but-present document would satisfy `toEqual` and be exactly the bug this file is about.
    expect(result.current).toStrictEqual(READY_ON_FRESH)

    expectPingPongNotRepeated(loadEditorDocumentMock)
  })
})
