import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useGeneration } from '../useGeneration'
import { clearSession, saveSession } from '../../../auth/utils/authSession'

// The generation half of the H9.4 `send` carve-out — same missing guard as
// `ManualEditor.initServerError.test.tsx`, different caller. `useGeneration.resilience.test.ts`
// mocks `generationApi` and hands the hook `new Error('… (HTTP 502)')`, a shape `send` no longer
// emits, so it cannot see a 5xx collapsing to the generic string here. This drives the real
// `fetch` → `httpClient` → `send` → `generationApi` chain and asserts what the user is told.
describe('useGeneration server errors reach the user through the real send chain', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  function stubServerError(body: Record<string, unknown>): void {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response(JSON.stringify(body), { status: 500 }))),
    )
  }

  async function submitAndFail(body: Record<string, unknown>): Promise<string | null> {
    stubServerError(body)
    const { result } = renderHook(() => useGeneration())
    await act(async () => {
      await result.current.submit('тема')
    })
    expect(result.current.state).toBe('failed')
    return result.current.error
  }

  it("shows the origin's message when creating the generation 500s", async () => {
    expect(await submitAndFail({ error_code: 'INTERNAL_ERROR', message: 'Сервис недоступен' })).toBe(
      'Сервис недоступен',
    )
  })

  // No readable text — the status is the only fact left and must not be discarded.
  it('keeps the status visible when the 500 body carries no readable text', async () => {
    expect(await submitAndFail({})).toBe('Не удалось создать запрос (HTTP 500)')
  })
})
