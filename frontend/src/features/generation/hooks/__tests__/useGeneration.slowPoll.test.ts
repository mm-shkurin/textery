import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useGeneration } from '../useGeneration'
import * as api from '../../api/generationApi'

vi.mock('../../api/generationApi')

const POLL_INTERVAL_MS = 5000

function pending() {
  return {
    generationId: 'gen-1',
    status: 'pending' as const,
    content: null,
    topic: 't',
    volumePages: 5,
    documentType: 'doklad',
    createdAt: 'now',
  }
}

describe('useGeneration when the status endpoint is slower than the poll interval', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  // The interval is 5s; the shared request timeout allows 25s. Without a guard, a backend taking
  // longer than one interval gets a second request on every tick while the first is still out —
  // up to five concurrent status calls for a single generation, growing with the delay.
  it('does not stack a second status call on top of one still in flight', async () => {
    vi.mocked(api.createGeneration).mockResolvedValue({ generationId: 'gen-1', status: 'pending' })
    let releaseFirst: (value: ReturnType<typeof pending>) => void = () => {}
    vi.mocked(api.getGeneration).mockImplementation(
      () =>
        new Promise((resolve) => {
          releaseFirst = resolve
        }),
    )

    const { result } = renderHook(() => useGeneration())
    await act(async () => {
      result.current.submit('тема')
    })

    // Three ticks pass while the very first check is still unanswered.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 3)
    })

    expect(api.getGeneration).toHaveBeenCalledTimes(1)

    // Once it answers, polling resumes normally — the guard skips ticks, it does not end the poll.
    await act(async () => {
      releaseFirst(pending())
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS)
    })

    expect(api.getGeneration).toHaveBeenCalledTimes(2)
    expect(result.current.state).toBe('pending')
  })

  // The attempt counter is the real casualty of stacking: each queued call spends one, so the
  // 60-attempt (~5 minute) budget would drain in a fraction of that and the user would be told
  // the generation timed out while it was still running.
  it('spends no attempt on a tick it skipped', async () => {
    vi.mocked(api.createGeneration).mockResolvedValue({ generationId: 'gen-1', status: 'pending' })
    let release: (value: ReturnType<typeof pending>) => void = () => {}
    vi.mocked(api.getGeneration).mockImplementation(
      () =>
        new Promise((resolve) => {
          release = resolve
        }),
    )

    const { result } = renderHook(() => useGeneration())
    await act(async () => {
      result.current.submit('тема')
    })

    // 100 ticks — well past MAX_POLL_ATTEMPTS = 60 — all against one unanswered request.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 100)
    })

    // Still pending, not "Превышено время ожидания генерации": no time-based budget was spent.
    expect(result.current.state).toBe('pending')
    expect(result.current.error).toBeNull()

    await act(async () => {
      release(pending())
    })
    expect(result.current.state).toBe('pending')
  })
})
