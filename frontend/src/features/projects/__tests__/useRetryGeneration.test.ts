import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { useRetryGeneration } from '../hooks/useRetryGeneration'
import { RETRY_FAILURE_FALLBACK, retryGeneration } from '../api/retryGenerationApi'

vi.mock('../api/retryGenerationApi', async (importOriginal) => {
  // The constants are the real ones — a hand-written copy of the fallback sentence here would let
  // the module's wording drift while this suite kept asserting the old string.
  const actual = await importOriginal<typeof import('../api/retryGenerationApi')>()
  return { ...actual, retryGeneration: vi.fn() }
})

// «Повторить» bills a model. Every guard in this hook exists because the failure mode is not a
// broken screen but a second charged generation, so each one is pinned by the sequence that would
// produce the double: two clicks in one tick, and a retry after a request whose response was lost.
describe('useRetryGeneration', () => {
  const mockedRetry = vi.mocked(retryGeneration)

  beforeEach(() => {
    mockedRetry.mockResolvedValue({ id: 'g-1', status: 'queued' })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  // A promise the test settles by hand, so the in-flight state can be observed rather than
  // inferred from the state after it is over.
  function deferred() {
    let resolve!: () => void
    let reject!: (error: unknown) => void
    const promise = new Promise<{ id: string; status: string }>((res, rej) => {
      resolve = () => res({ id: 'g-1', status: 'queued' })
      reject = rej
    })
    return { promise, resolve, reject }
  }

  it('marks the source pending while its request is in flight and clears it on success', async () => {
    const gate = deferred()
    mockedRetry.mockReturnValue(gate.promise)
    const onRetried = vi.fn()
    const { result } = renderHook(() => useRetryGeneration(onRetried))

    expect(result.current.pendingId).toBeNull()

    act(() => void result.current.retry('g-1'))
    await waitFor(() => expect(result.current.pendingId).toBe('g-1'))
    // Nothing is refetched while the server has not answered: a feed reloaded here would paint the
    // list as it was BEFORE the retry and read as «nothing happened».
    expect(onRetried).not.toHaveBeenCalled()

    await act(async () => {
      gate.resolve()
      await gate.promise
    })

    expect(result.current.pendingId).toBeNull()
    expect(result.current.error).toBeNull()
    // Refetch rather than splice the new row in locally: the server decides the order.
    expect(onRetried).toHaveBeenCalledTimes(1)
  })

  it('sends the generation id with an idempotency key', async () => {
    const { result } = renderHook(() => useRetryGeneration(vi.fn()))

    await act(async () => {
      await result.current.retry('g-7')
    })

    expect(mockedRetry).toHaveBeenCalledTimes(1)
    const [id, key] = mockedRetry.mock.calls[0]
    expect(id).toBe('g-7')
    // The shape, not merely non-empty: the header's whole job is to be unique per attempt, and a
    // constant like 'retry' would satisfy `toBeTruthy` while collapsing every user's retries onto
    // one server-side record.
    expect(key).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/)
  })

  // Two clicks in the same tick both read the state value from before the first render, which is
  // why the in-flight guard is a ref. A state-based guard passes a test that awaits between the
  // clicks and fails this one.
  it('ignores a second click on a source whose request has not returned', async () => {
    const gate = deferred()
    mockedRetry.mockReturnValue(gate.promise)
    const { result } = renderHook(() => useRetryGeneration(vi.fn()))

    act(() => {
      void result.current.retry('g-1')
      void result.current.retry('g-1')
    })

    expect(mockedRetry).toHaveBeenCalledTimes(1)

    await act(async () => {
      gate.resolve()
      await gate.promise
    })
    expect(mockedRetry).toHaveBeenCalledTimes(1)
  })

  // The guard is per SOURCE, not a global "one retry at a time": two failed generations are two
  // independent commands, and blocking the second would look like a dead button.
  it('lets a different source start while one is in flight', async () => {
    const gate = deferred()
    mockedRetry.mockReturnValueOnce(gate.promise)
    const { result } = renderHook(() => useRetryGeneration(vi.fn()))

    act(() => {
      void result.current.retry('g-1')
      void result.current.retry('g-2')
    })

    expect(mockedRetry).toHaveBeenCalledTimes(2)
    expect(mockedRetry.mock.calls.map(([id]) => id)).toEqual(['g-1', 'g-2'])

    await act(async () => {
      gate.resolve()
      await gate.promise
    })
  })

  it('names the failing source in the error and does not refetch', async () => {
    mockedRetry.mockRejectedValue(new Error('Сеть недоступна'))
    const onRetried = vi.fn()
    const { result } = renderHook(() => useRetryGeneration(onRetried))

    await act(async () => {
      await result.current.retry('g-3')
    })

    // Scoped to the card that failed — a page-level banner leaves the user hunting for which of
    // twenty cards the sentence is about.
    expect(result.current.error).toEqual({ id: 'g-3', message: 'Сеть недоступна' })
    expect(result.current.pendingId).toBeNull()
    expect(onRetried).not.toHaveBeenCalled()
  })

  // A bare `HttpError` is an object literal, not an `Error`, so `.message` on it is `undefined`.
  // `describeFailure` is what keeps 'undefined' off the card.
  it('falls back to the retry sentence when the failure carries no text', async () => {
    mockedRetry.mockRejectedValue({ status: 503 })
    const { result } = renderHook(() => useRetryGeneration(vi.fn()))

    await act(async () => {
      await result.current.retry('g-4')
    })

    expect(result.current.error).toEqual({ id: 'g-4', message: RETRY_FAILURE_FALLBACK })
  })
})
