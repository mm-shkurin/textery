import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from 'vitest'
import { useGeneration } from '../useGeneration'
import { clearSession, saveSession } from '../../../auth/utils/authSession'

// The POLL half of the H9.4 `send` carve-out. `useGeneration.serverError.test.ts` drives the real
// chain only through `submit` — the `:140` catch — so the give-up catch at `useGeneration.ts:101`,
// which the same unit changed from `e.message` to `describeFailure(e, …)`, has nothing that can see
// it. The suites that DO exercise the `MAX_CONSECUTIVE_POLL_FAILURES` branch
// (`useGeneration.resilience.test.ts:66,82-87`) carry `vi.mock('../../api/generationApi')` and
// reject with `new Error('Ошибка сети')` / `new Error('blip')` — the exact shape `send` no longer
// emits for a 5xx, since a 5xx now arrives as a bare `HttpError` object with no `.message` at all.
//
// Revert that one line to `e instanceof Error ? e.message : 'Ошибка сети'` and every other suite in
// the repo stays green while a real polling 5xx shows the bare fallback and throws the status away
// — the one fact a user can quote when reporting a poll that gave up. So this file mocks `fetch`
// and lets `httpClient` → `send` → `generationApi` run for real.
//
// Session seeded because every call goes through `authorizedRequest`: without a token the request
// never reaches the transport and the 500 under test is unreachable.
const POLL_INTERVAL_MS = 5000
const GENERATION_ID = 'gen-1'
const TOPIC = 'тема'
const ACCESS_TOKEN = 'access-1'
const CREATE_REQUEST = 'POST /api/v1/generations'
const STATUS_REQUEST = `GET /api/v1/generations/${GENERATION_ID}`

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

// One run of the give-up path, as data: no assertion lives in here, so every failure is
// attributable to the `it` that made the claim.
interface GiveUpRun {
  // `state` sampled after submit, after tick 1, after tick 2, and after one further tick.
  states: string[]
  // Cumulative `METHOD /path` log sampled at those same four points.
  requests: string[][]
  authorizationHeaders: string[]
  terminal: Observed
}

// Typed so `mock.calls` destructures as a fixed pair rather than `any[]` — the request log below
// reads both elements, and an untyped mock would let a typo there through the build.
let fetchMock: Mock<(input: string, init: RequestInit) => Promise<Response>>

describe('useGeneration — a poll that gives up on a 5xx says which status it gave up on', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    saveSession({ accessToken: ACCESS_TOKEN, refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  // The create SUCCEEDS and every status check 500s — the shape this branch exists for. Scripted by
  // request kind rather than by call order so the responses do not silently depend on how many
  // requests the hook makes to get there. Pure scripting: the URLs it was actually called with are
  // asserted afterwards, from `fetchMock.mock.calls`, where a mismatch cannot be swallowed by the
  // hook's own catch and reported as a poll failure.
  function stubCreateThenFailingStatus(statusBody: Record<string, unknown>): void {
    fetchMock = vi.fn((_input: string, init: RequestInit) =>
      Promise.resolve(
        init.method === 'POST'
          ? new Response(JSON.stringify({ generation_id: GENERATION_ID, status: 'pending' }), {
              status: 201,
            })
          : new Response(JSON.stringify(statusBody), { status: 500 }),
      ),
    )
    vi.stubGlobal('fetch', fetchMock)
  }

  function requestLog(): string[] {
    return fetchMock.mock.calls.map(([input, init]) => `${init.method} ${input}`)
  }

  function authorizationHeaders(): string[] {
    return fetchMock.mock.calls.map(
      ([, init]) => (init.headers as Record<string, string>).Authorization,
    )
  }

  // Submit fires the immediate first check; the two ticks are failures 2 and 3, which is the
  // MAX_CONSECUTIVE_POLL_FAILURES ceiling. The fourth sample is one tick PAST the give-up: its
  // request log is what proves `stopPolling()` ran, since a give-up that leaves the interval alive
  // reaches the same terminal state and reads identically.
  async function driveUntilItGivesUp(statusBody: Record<string, unknown>): Promise<GiveUpRun> {
    stubCreateThenFailingStatus(statusBody)
    const { result } = renderHook(() => useGeneration())
    const states: string[] = []
    const requests: string[][] = []

    await act(async () => {
      await result.current.submit(TOPIC)
    })
    states.push(result.current.state)
    requests.push(requestLog())

    for (let tick = 0; tick < 3; tick += 1) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS)
      })
      states.push(result.current.state)
      requests.push(requestLog())
    }

    return {
      states,
      requests,
      authorizationHeaders: authorizationHeaders(),
      terminal: {
        state: result.current.state,
        content: result.current.content,
        volumePages: result.current.volumePages,
        createdAt: result.current.createdAt,
        error: result.current.error,
      },
    }
  }

  // The generation itself was never reported failed by the server — the poll gave up on it. So
  // there is nothing to show, and any field left over from a previous run would be a lie.
  function expectGaveUpWith(run: GiveUpRun, message: string): void {
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
    expect(run.requests).toEqual([
      [CREATE_REQUEST, STATUS_REQUEST],
      [CREATE_REQUEST, STATUS_REQUEST, STATUS_REQUEST],
      [CREATE_REQUEST, STATUS_REQUEST, STATUS_REQUEST, STATUS_REQUEST],
      // Unchanged one tick past the give-up: the interval was cleared, not left running.
      [CREATE_REQUEST, STATUS_REQUEST, STATUS_REQUEST, STATUS_REQUEST],
    ])
    // Every one of those four requests carried the seeded session, so the 500 under test is the
    // origin refusing — not the transport declining to send, and not a 401 replay path.
    expect(run.authorizationHeaders).toEqual(Array(4).fill(`Bearer ${ACCESS_TOKEN}`))
  }

  it("shows the origin's message when the status endpoint 500s past the tolerance", async () => {
    const run = await driveUntilItGivesUp({
      error_code: 'INTERNAL_ERROR',
      message: 'Статус недоступен',
    })
    expectGaveUpWith(run, 'Статус недоступен')
  })

  // No readable text in the body — a proxy's own error page, or an origin that answered with none.
  // The status is then the only fact left, and it is the whole reason this catch stopped reading
  // `.message`: an `HttpError` is a bare object literal, so `.message` is `undefined` there and the
  // user would be told «Ошибка сети» with nothing to quote.
  it('keeps the status visible when the failing status check carries no readable text', async () => {
    expectGaveUpWith(await driveUntilItGivesUp({}), 'Ошибка сети (HTTP 500)')
  })
})
