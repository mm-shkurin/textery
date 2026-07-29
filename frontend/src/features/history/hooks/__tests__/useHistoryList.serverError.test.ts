import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { useHistoryList } from '../useHistoryList'
import { listDocuments, type DocumentSummary } from '../../api/historyApi'
import {
  ORIGIN_INTERNAL_ERROR_BODY,
  ORIGIN_PROVIDER_UNAVAILABLE_BODY,
} from '../../../../shared/api/__tests__/originErrorBodies'
import {
  ACCESS_TOKEN,
  authorizationHeaders,
  requestLog,
  resetSession,
  seedSession,
  stubOriginError,
} from '../../../../shared/api/__tests__/originStubs'

// The history half of the H9.4 `send` carve-out. This caller had NO 5xx case anywhere — neither
// `historyApi.test.ts` nor the HistoryPage suites (which `vi.mock` the whole api module) — so it
// had no tripwire at all against a 5xx now arriving as a bare `HttpError` object and collapsing
// to the generic string at `useHistoryList`'s catch. Real `fetch` → `httpClient` → `send` →
// `historyApi` chain, asserting what the user is told.
const LIST_REQUEST = 'GET /api/v1/documents?limit=20'

// The hook's whole observable surface. `error` alone cannot see a failed load that leaves
// `isLoading` true forever (a spinner that never stops), that leaves `hasMore` on so «показать
// ещё» invites a click into the same 500, or that leaves stale rows on screen beside the banner.
interface Observed {
  items: DocumentSummary[]
  isLoading: boolean
  error: string | null
  hasMore: boolean
  requests: string[]
  authorizationHeaders: string[]
}

describe('useHistoryList server errors reach the user through the real send chain', () => {
  beforeEach(seedSession)
  afterEach(resetSession)

  // Gated on `isLoading` settling, NOT on `error` being non-null: waiting on the very value under
  // test lets a transient wrong string satisfy the gate, and leaves the terminal `error` read
  // racing the render that set it. No assertion on the outcome lives in here.
  async function loadAndObserve(body: Record<string, unknown>): Promise<Observed> {
    const fetchMock = stubOriginError(body)
    const { result } = renderHook(() => useHistoryList(() => listDocuments()))
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })
    return {
      items: result.current.items,
      isLoading: result.current.isLoading,
      error: result.current.error,
      hasMore: result.current.hasMore,
      requests: requestLog(fetchMock),
      authorizationHeaders: authorizationHeaders(fetchMock),
    }
  }

  // Nothing loaded, so the list is empty and there is no next page to offer. One request, carrying
  // the seeded session — so the 500 is the origin refusing, not the transport declining to send.
  function expectFailedWith(observed: Observed, error: string): void {
    expect(observed).toEqual({
      items: [],
      isLoading: false,
      error,
      hasMore: false,
      requests: [LIST_REQUEST],
      authorizationHeaders: [`Bearer ${ACCESS_TOKEN}`],
    })
  }

  // H9.4, `useHistoryList.ts:56`. The origin's catch-all 500 is measured and ENGLISH; the list's
  // own Russian fallback plus the status is what a person is shown instead. The case below stubbed
  // this same code with a hand-rolled Russian message, so the English was invisible here.
  // RED: error is 'An unexpected error occurred. Please try again.' instead of
  // 'Не удалось загрузить список (HTTP 500)'. Un-skip in green-frontend.
  it.skip("does not show the catch-all 500's English text when the documents list fails", async () => {
    expectFailedWith(
      await loadAndObserve(ORIGIN_INTERNAL_ERROR_BODY),
      'Не удалось загрузить список (HTTP 500)',
    )
  })

  // An EXPLAINED 5xx keeps its text — the carve-out is keyed on the catch-all code, not the status.
  it("shows the origin's message when the documents list hits an explained 5xx", async () => {
    expectFailedWith(
      await loadAndObserve(ORIGIN_PROVIDER_UNAVAILABLE_BODY),
      ORIGIN_PROVIDER_UNAVAILABLE_BODY.message,
    )
  })

  // No readable text — the status is the only fact left and must not be discarded. The fallback
  // is the HOOK's, not `historyApi`'s ('Не удалось загрузить документы'): the api-layer fallback
  // only ever reached the user through the flatten `send` no longer performs for 5xx, so this
  // pins which of the two strings a person now actually sees.
  it('keeps the status visible when the 500 body carries no readable text', async () => {
    expectFailedWith(await loadAndObserve({}), 'Не удалось загрузить список (HTTP 500)')
  })
})
