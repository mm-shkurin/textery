import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useRetryGeneration } from '../useRetryGeneration'
import { retryGeneration } from '../api/retryGenerationApi'

vi.mock('../api/retryGenerationApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/retryGenerationApi')>()
  return { ...actual, retryGeneration: vi.fn() }
})

/**
 * The lifetime of the `Idempotency-Key`, which is the whole reason the hook keeps a Map at all.
 *
 * The two directions are opposite and both are money:
 *
 *   - after a FAILURE the key is KEPT, because the most dangerous failure is the one where the
 *     request reached the server and the response did not come back. A fresh key on the next click
 *     would start a second generation for work that is already running and already billed.
 *   - after a SUCCESS the key is DROPPED, because the user's next «Повторить» on that row is a
 *     genuinely new command. Reusing the key would make it a no-op the server collapses onto the
 *     generation it already produced, and the button would look broken.
 *
 * Neither can be read off the state the hook exposes; both are only visible in the argument the
 * client is called with, which is why this suite asserts on the recorded calls.
 */
describe('useRetryGeneration idempotency key', () => {
  const mockedRetry = vi.mocked(retryGeneration)

  beforeEach(() => {
    mockedRetry.mockResolvedValue({ id: 'g-1', status: 'queued' })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  function keysUsed(): string[] {
    return mockedRetry.mock.calls.map(([, key]) => key)
  }

  it('replays the same key after a failed attempt on the same source', async () => {
    mockedRetry.mockRejectedValueOnce(new Error('таймаут'))
    const { result } = renderHook(() => useRetryGeneration(vi.fn()))

    await act(async () => {
      await result.current.retry('g-1')
    })
    await act(async () => {
      await result.current.retry('g-1')
    })

    expect(mockedRetry).toHaveBeenCalledTimes(2)
    const [first, second] = keysUsed()
    expect(second).toBe(first)
  })

  it('mints a fresh key for the next attempt after one succeeds', async () => {
    const { result } = renderHook(() => useRetryGeneration(vi.fn()))

    await act(async () => {
      await result.current.retry('g-1')
    })
    await act(async () => {
      await result.current.retry('g-1')
    })

    expect(mockedRetry).toHaveBeenCalledTimes(2)
    const [first, second] = keysUsed()
    expect(second).not.toBe(first)
  })

  // Two rows are two commands. A single shared key would let the server treat the second row's
  // retry as a replay of the first and silently do nothing.
  it('gives each source its own key', async () => {
    const { result } = renderHook(() => useRetryGeneration(vi.fn()))

    await act(async () => {
      await result.current.retry('g-1')
    })
    await act(async () => {
      await result.current.retry('g-2')
    })

    const [first, second] = keysUsed()
    expect(second).not.toBe(first)
  })
})
