import { renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useHistoryList } from '../useHistoryList'
import { listDocuments } from '../../api/historyApi'
import { clearSession, saveSession } from '../../../auth/utils/authSession'

// The history half of the H9.4 `send` carve-out. This caller had NO 5xx case anywhere — neither
// `historyApi.test.ts` nor the HistoryPage suites (which `vi.mock` the whole api module) — so it
// had no tripwire at all against a 5xx now arriving as a bare `HttpError` object and collapsing
// to the generic string at `useHistoryList`'s catch. Real `fetch` → `httpClient` → `send` →
// `historyApi` chain, asserting what the user is told.
describe('useHistoryList server errors reach the user through the real send chain', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  async function loadAndFail(body: Record<string, unknown>): Promise<string | null> {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response(JSON.stringify(body), { status: 500 }))),
    )
    const { result } = renderHook(() => useHistoryList(() => listDocuments()))
    await waitFor(() => {
      expect(result.current.error).not.toBeNull()
    })
    return result.current.error
  }

  it("shows the origin's message when the documents list 500s", async () => {
    expect(await loadAndFail({ error_code: 'INTERNAL_ERROR', message: 'Список недоступен' })).toBe(
      'Список недоступен',
    )
  })

  // No readable text — the status is the only fact left and must not be discarded. The fallback
  // is the HOOK's, not `historyApi`'s ('Не удалось загрузить документы'): the api-layer fallback
  // only ever reached the user through the flatten `send` no longer performs for 5xx, so this
  // pins which of the two strings a person now actually sees.
  it('keeps the status visible when the 500 body carries no readable text', async () => {
    expect(await loadAndFail({})).toBe('Не удалось загрузить список (HTTP 500)')
  })
})
