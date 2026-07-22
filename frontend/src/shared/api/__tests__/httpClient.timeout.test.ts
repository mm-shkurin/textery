import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { REQUEST_TIMEOUT_MS, RequestTimeoutError, request } from '../httpClient'

// The shared client-side timeout (constraints C + D on Story 7 scenario 5.6). This transport is
// used by EVERY flow, so the bound and the no-retry guarantee are pinned here, one layer below
// the auth forms, on fake timers.

function okResponse(): Response {
  return new Response(JSON.stringify({ ok: true }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

// A fetch that resolves only after `delayMs` of fake time — models a slow-but-valid flow.
function fetchResolvingAfter(delayMs: number): () => Promise<Response> {
  return () =>
    new Promise<Response>((resolve) => {
      setTimeout(() => resolve(okResponse()), delayMs)
    })
}

const NEVER_SETTLES = (): Promise<Response> => new Promise<Response>(() => {})

describe('httpClient request timeout', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  // (C) The bound must clear the slowest legitimate flow's budget. A real document generation can
  // take ~20s+, so this floor pins that a future edit lowering the bound below that budget goes
  // RED here rather than silently aborting valid generations in production.
  it('sets a bound generous enough for the slowest legitimate flow (>= 20s)', () => {
    expect(REQUEST_TIMEOUT_MS).toBeGreaterThanOrEqual(20_000)
  })

  // (C) A request that settles JUST UNDER the bound still resolves — the timeout does not fire on
  // a slow-but-valid response.
  it('resolves a request that settles just under the bound', async () => {
    vi.stubGlobal('fetch', vi.fn(fetchResolvingAfter(REQUEST_TIMEOUT_MS - 1_000)))

    const pending = request<{ ok: boolean }>('/api/v1/slow')
    await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS - 1_000)

    await expect(pending).resolves.toEqual({ ok: true })
  })

  // A request that never settles rejects with RequestTimeoutError once the bound elapses — the
  // hang is converted into a rejection on the timer alone (the stub ignores any abort signal).
  it('rejects a hung request with RequestTimeoutError at the bound', async () => {
    vi.stubGlobal('fetch', vi.fn(NEVER_SETTLES))

    const pending = request('/api/v1/hangs')
    const assertion = expect(pending).rejects.toBeInstanceOf(RequestTimeoutError)
    await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS)

    await assertion
  })

  // (D) HIGHEST severity — a timed-out mutating POST is NOT silently retried into a duplicate.
  // The client stops WAITING; it never replays the request. fetch is called exactly once, so a
  // POST the server may already be processing is never fired a second time by the transport.
  it('does not auto-retry a timed-out mutating POST (no duplicate request)', async () => {
    const fetchMock = vi.fn(NEVER_SETTLES)
    vi.stubGlobal('fetch', fetchMock)

    const pending = request('/api/v1/generations', { method: 'POST', body: { topic: 'x' } })
    const assertion = expect(pending).rejects.toBeInstanceOf(RequestTimeoutError)
    await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS)
    await assertion

    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})
