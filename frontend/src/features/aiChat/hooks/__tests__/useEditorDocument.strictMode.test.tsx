import { StrictMode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useEditorDocument } from '../useEditorDocument'
import { loadEditorDocument } from '../../api/editorDocumentApi'

// Story 19, Frontend Scenario 0.1 — the coverage-inserted guard step "repeat mount does not
// refetch" (branches were 4/8: the true arm of `if (requestedIdRef.current === documentId) return`
// was taken by no test, so the whole `return` was deletable with the suite green).
//
// WHY THE EXISTING TESTS DO NOT COVER IT.
// `DocumentEditorPage.notFound.test.tsx` already asserts `toHaveBeenCalledExactlyOnceWith`, but it
// renders OUTSIDE StrictMode. Without the double-invoke the effect runs once anyway, so that
// assertion passes unchanged against a hook with no guard at all — it pins the ARGUMENT, not the
// deduplication. `generation/hooks/__tests__/useDocumentInit.strictMode.test.tsx` does exercise
// StrictMode, but for a different hook and a different defect (one idempotency key per mount).
//
// WHY A COUNT HERE, WHERE useDocumentInit ASSERTS RELATIONALLY.
// useDocumentInit's guarantee survives the effect running twice — two calls carrying one key are a
// request and its replay — so pinning a count there would have made that test about React's dev
// behaviour. Here the guarantee IS "the fetch does not repeat", and there is no weaker form of it:
// the count is the specification. That makes this file's own load-bearingness depend on React
// genuinely double-invoking under StrictMode in this environment — verified by mutation, not
// assumed: deleting the guard line makes the first expectation below report 2 calls.
//
// WHY THE FETCH AND NOT THE setState.
// The cleanup-flag pattern used by useDocumentInit suppresses the second run's setState but leaves
// its request in flight. `/documents/{id}` is a read, so a duplicate is not a correctness bug in
// the backend — it is a doubled request on every editor open, and the response ordering it invites
// is what the ref's second role (the stale-response check) exists to survive. The guard must sit
// BEFORE the call, and only a call-count assertion can tell that apart from a guard that sits after.
//
// WHY THE SECOND TEST CHANGES THE ID RATHER THAN RE-RENDERING WITH THE SAME ONE.
// An earlier draft of this file called `rerender()` with the id unchanged and leaned on the same
// count assertion. That half was vacuous and measured as such: with `[documentId]` unchanged the
// effect does not re-run whether or not the guard exists, so with the guard line deleted the count
// came out at 2 (the double-invoke) and not 3 — the rerender contributed no independent failure.
// What IS unpinned is the guard's KEY. Degrading it to `if (requestedIdRef.current !== null) return`
// — "fetch at most once ever, whatever the id" — passed the entire suite, 513/513, because nothing
// ever asked this hook for a second document. That mutation is what the second test kills.
//
// DELIBERATELY NOT PINNED HERE: a response arriving for a documentId that is no longer the
// requested one. That is the sibling step "stale response for old id ignored", a separate unit —
// it is about which response WINS, not about which requests are issued.

const DOCUMENT_ID = '7a3d5e19-2c64-4b08-8f52-91ad3e7c0b6f'
const OTHER_DOCUMENT_ID = 'c81b0f4a-6d27-4e93-a05c-3fb27de41859'

const DOCUMENT = {
  documentId: DOCUMENT_ID,
  content: '<p>Введение к докладу</p>',
  version: 3,
}
const OTHER_DOCUMENT = {
  documentId: OTHER_DOCUMENT_ID,
  content: '<p>Тезисы второго доклада</p>',
  version: 1,
}

vi.mock('../../api/editorDocumentApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/editorDocumentApi')>()
  return { ...actual, loadEditorDocument: vi.fn() }
})

const loadEditorDocumentMock = vi.mocked(loadEditorDocument)

describe('useEditorDocument under StrictMode', () => {
  beforeEach(() => {
    loadEditorDocumentMock.mockReset()
  })

  it('loads the document once per mount, even though the effect is invoked twice', async () => {
    loadEditorDocumentMock.mockResolvedValue(DOCUMENT)

    const { result } = renderHook(() => useEditorDocument(DOCUMENT_ID), { wrapper: StrictMode })

    // Awaited on the SETTLED state, not on the call count: `toHaveBeenCalledOnce` would be
    // satisfiable the instant the first invocation fires, before a second one had any chance to,
    // making the count check below a race that passes for the wrong reason.
    await waitFor(() => {
      expect(result.current.status).toBe('ready')
    })

    // The whole state, not just `status`: the guard sits before the fetch, so a guard that also
    // swallowed the setState would leave `status: 'ready'` reachable with no document behind it.
    expect(result.current).toEqual({ status: 'ready', document: DOCUMENT })
    expect(loadEditorDocumentMock).toHaveBeenCalledExactlyOnceWith(DOCUMENT_ID)
  })

  it('fetches again when the id changes — the guard is keyed to the id, not to "already loaded"', async () => {
    loadEditorDocumentMock.mockImplementation(async (documentId: string) =>
      documentId === DOCUMENT_ID ? DOCUMENT : OTHER_DOCUMENT,
    )

    const { result, rerender } = renderHook(
      ({ documentId }: { documentId: string }) => useEditorDocument(documentId),
      { wrapper: StrictMode, initialProps: { documentId: DOCUMENT_ID } },
    )

    await waitFor(() => {
      expect(result.current).toEqual({ status: 'ready', document: DOCUMENT })
    })

    rerender({ documentId: OTHER_DOCUMENT_ID })

    // Synchronously after the re-render, before the new response lands: the previous document must
    // already be gone. Leaving it on screen would show the user one document's text under another
    // document's id for the length of a round trip.
    expect(result.current).toEqual({ status: 'loading' })

    await waitFor(() => {
      expect(result.current).toEqual({ status: 'ready', document: OTHER_DOCUMENT })
    })

    // Exact calls, in order — pins the count (no re-fetch of the first id) and the arguments
    // together, which two separate count/argument assertions would not.
    expect(loadEditorDocumentMock.mock.calls).toEqual([[DOCUMENT_ID], [OTHER_DOCUMENT_ID]])
  })
})
