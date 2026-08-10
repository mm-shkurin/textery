import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, waitFor } from '@testing-library/react'
import { DocumentNotFoundError, loadEditorDocument } from '../../api/editorDocumentApi'
import {
  FRESH_DOCUMENT,
  READY_ON_FRESH,
  expectPingPongNotRepeated,
  startPingPong,
} from './supersededRequestFixture'

// Story 19, Frontend Scenario 0.1 — coverage step "a superseded *rejection* for the SAME id loses".
//
// THE `.catch` TWIN OF `useEditorDocument.supersededResponse.test.tsx`, which no test reached:
// deleting `if (requestTokenRef.current !== requestToken) return` from the hook's `.catch` left the
// whole of `src/features/aiChat` green.
//
// THIS IS THE WORSE OF THE TWO ARMS. The `.then` arm installs a stale-but-plausible document — the
// user sees real text and only the hidden `version` is wrong. This arm replaces a good `ready` with
// a dead end: `failed`, or `not-found`, which per the hook's own comment tells the user their
// document is gone and invites them to re-create one that already exists.
//
// A REJECTION IS NOT THE RARER CASE. The abandoned leg of a route ping-pong is precisely the
// request most likely to be answered by a 502, a dropped connection or an expired session, and a
// `DocumentNotFoundError` is the sharpest of them.
//
// UNLIKE ITS SIBLING, THIS CASE PASSES AGAINST UNMODIFIED MAIN. It pins an existing, correct guard
// rather than driving new behavior, so its RED evidence is mutation, not a failing main — the same
// shape as `useEditorDocument.strictMode.test.tsx`. With the `.catch` guard line deleted:
//
//   AssertionError: expected { status: 'not-found' } to strictly equal
//                   { status: 'ready', document: { …version: 9 } }
//
// and every earlier assertion still passed, which is what makes the case non-vacuous. The line was
// restored immediately; the hook's diff is empty.

vi.mock('../../api/editorDocumentApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/editorDocumentApi')>()
  return { ...actual, loadEditorDocument: vi.fn() }
})

const loadEditorDocumentMock = vi.mocked(loadEditorDocument)

describe('useEditorDocument when the superseded request for the same document fails', () => {
  beforeEach(() => {
    loadEditorDocumentMock.mockReset()
  })

  it('keeps the newest response when the superseded request for the same id rejects last', async () => {
    const { result, resolvers, rejecters } = startPingPong(loadEditorDocumentMock)

    // The second request for A answers first and succeeds — the good state the late failure must
    // not be allowed to destroy.
    await act(async () => {
      resolvers[2](FRESH_DOCUMENT)
    })
    await waitFor(() => {
      expect(result.current).toStrictEqual(READY_ON_FRESH)
    })

    // …and only now the first, superseded request for A comes back — as a failure.
    await act(async () => {
      rejecters[0](new DocumentNotFoundError())
    })

    // Whole state via `toStrictEqual`, for the same two reasons as the sibling file: a hook that
    // dropped the rejection by falling back to `{ status: 'loading' }` would also be wrong, and
    // `toEqual` would accept a union widened to carry an `error?` beside the surviving document.
    expect(result.current).toStrictEqual(READY_ON_FRESH)

    expectPingPongNotRepeated(loadEditorDocumentMock)
  })
})
