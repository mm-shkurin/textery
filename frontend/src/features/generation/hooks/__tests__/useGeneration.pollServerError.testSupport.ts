// Test support for `useGeneration.pollServerError.test.ts` — the request script, the fake-timer
// drive, and the give-up assertion vocabulary. Extracted so the test class holds only the claims:
// the scripting and the mock-call readback are transport infrastructure, not scenario narrative.
import { act, renderHook } from '@testing-library/react'
import { expect, vi } from 'vitest'
import { useGeneration } from '../useGeneration'
import {
  ACCESS_TOKEN,
  authorizationHeaders,
  originResponse,
  requestLog,
  type FetchMock,
} from '../../../../shared/api/__tests__/originStubs'

const POLL_INTERVAL_MS = 5000
const GENERATION_ID = 'gen-1'
const TOPIC = 'тема'
const CREATE_REQUEST = 'POST /api/v1/generations'
const STATUS_REQUEST = `GET /api/v1/generations/${GENERATION_ID}`

// `MAX_CONSECUTIVE_POLL_FAILURES` (useGeneration.ts:22). Submit fires the immediate first check,
// so the drive needs CEILING ticks to reach the ceiling and one more to observe that the interval
// was cleared — named, because as a bare `3` a moved production ceiling would silently drive the
// wrong number of ticks and fail as an opaque array diff.
const POLL_FAILURE_CEILING = 3

// What the hook exposes to the screen. Named so the terminal state is asserted as one whole object
// rather than field by field — a give-up that leaves `volumePages`/`createdAt` from an earlier
// completed run behind is the same lie the null `content` exists to prevent.
interface Observed {
  state: string
  content: string | null
  volumePages: number | null
  createdAt: string | null
  error: string | null
}

// One run of the give-up path, as data: no assertion lives in the driver, so every failure is
// attributable to the `it` that made the claim.
export interface GiveUpRun {
  // `state` sampled after submit and after each of the three ticks.
  states: string[]
  // Cumulative `METHOD /path` log sampled at those same four points.
  requests: string[][]
  authorizationHeaders: string[]
  terminal: Observed
}

// The create SUCCEEDS and every status check 500s — the shape this branch exists for. Scripted by
// request kind rather than by call order so the responses do not silently depend on how many
// requests the hook makes to get there. Pure scripting: the URLs it was actually called with are
// asserted afterwards, from the recorded calls, where a mismatch cannot be swallowed by the hook's
// own catch and reported as a poll failure.
function stubCreateThenFailingStatus(statusBody: Record<string, unknown>): FetchMock {
  const fetchMock: FetchMock = vi.fn((_input: string, init: RequestInit) =>
    Promise.resolve(
      init.method === 'POST'
        ? originResponse({ generation_id: GENERATION_ID, status: 'pending' }, 201)
        : originResponse(statusBody, 500),
    ),
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

export async function driveUntilItGivesUp(statusBody: Record<string, unknown>): Promise<GiveUpRun> {
  const fetchMock = stubCreateThenFailingStatus(statusBody)
  const { result } = renderHook(() => useGeneration())
  const states: string[] = []
  const requests: string[][] = []

  await act(async () => {
    await result.current.submit(TOPIC)
  })
  states.push(result.current.state)
  requests.push(requestLog(fetchMock))

  for (let tick = 0; tick < POLL_FAILURE_CEILING; tick += 1) {
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS)
    })
    states.push(result.current.state)
    requests.push(requestLog(fetchMock))
  }

  return {
    states,
    requests,
    authorizationHeaders: authorizationHeaders(fetchMock),
    terminal: {
      state: result.current.state,
      content: result.current.content,
      volumePages: result.current.volumePages,
      createdAt: result.current.createdAt,
      error: result.current.error,
    },
  }
}

// The cumulative log expected at each sample: one status check per sample, except the LAST, which
// is one tick PAST the give-up and must be unchanged — that repetition is what proves
// `stopPolling()` ran, since a give-up that left the interval alive reaches the same terminal
// state and reads identically everywhere else.
function expectedRequestLog(): string[][] {
  const checksPerSample = [1, 2, POLL_FAILURE_CEILING, POLL_FAILURE_CEILING]
  return checksPerSample.map((checks) => [CREATE_REQUEST, ...Array(checks).fill(STATUS_REQUEST)])
}

// The generation itself was never reported failed by the server — the poll gave up on it. So
// there is nothing to show, and any field left over from a previous run would be a lie.
export function expectGaveUpWith(run: GiveUpRun, message: string): void {
  expect(run.terminal).toEqual({
    state: 'failed',
    content: null,
    volumePages: null,
    createdAt: null,
    error: message,
  })
  // Two failed checks are NOT enough — this is what pins the ceiling itself. Without it a poll
  // that gave up on the FIRST 5xx, the regression the tolerance was added to prevent, passes.
  expect(run.states).toEqual(['pending', 'pending', 'failed', 'failed'])
  expect(run.requests).toEqual(expectedRequestLog())
  // Every request carried the seeded session, so the 500 under test is the origin refusing — not
  // the transport declining to send, and not a 401 replay path.
  expect(run.authorizationHeaders).toEqual(
    Array(1 + POLL_FAILURE_CEILING).fill(`Bearer ${ACCESS_TOKEN}`),
  )
}
