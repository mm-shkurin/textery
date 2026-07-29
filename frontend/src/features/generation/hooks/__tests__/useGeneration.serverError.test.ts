import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { useGeneration } from '../useGeneration'
import {
  ORIGIN_INTERNAL_ERROR_BODY,
  ORIGIN_PROVIDER_UNAVAILABLE_BODY,
} from '../../../../shared/api/__tests__/originErrorBodies'
import {
  ACCESS_TOKEN,
  authorizationHeaders,
  requestLog,
  resetOriginStubs,
  seedSession,
  stubOriginError,
} from '../../../../shared/api/__tests__/originStubs'

// The generation half of the H9.4 `send` carve-out — same missing guard as
// `ManualEditor.initServerError.test.tsx`, different caller. `useGeneration.resilience.test.ts`
// mocks `generationApi` and hands the hook `new Error('… (HTTP 502)')`, a shape `send` no longer
// emits, so it cannot see a 5xx collapsing to the generic string here. This drives the real
// `fetch` → `httpClient` → `send` → `generationApi` chain and asserts what the user is told.
const TOPIC = 'тема'
const CREATE_REQUEST = 'POST /api/v1/generations'

// The hook's whole observable surface, asserted as one object. A failed submit that leaves
// `content`/`volumePages`/`createdAt` behind from an earlier run is the same lie the null fields
// exist to prevent — asserting `error` alone cannot see it. Mirrors `Observed` in the sibling
// `useGeneration.pollServerError.test.ts`.
interface Observed {
  state: string
  content: string | null
  volumePages: number | null
  createdAt: string | null
  error: string | null
  requests: string[]
  authorizationHeaders: string[]
}

describe('useGeneration server errors reach the user through the real send chain', () => {
  beforeEach(seedSession)
  afterEach(resetOriginStubs)

  // No assertion in here — a hook that reached 'idle' must be reported against the `it` that
  // claimed 'failed', not against a line inside a shared setup step.
  async function submitAndObserve(body: Record<string, unknown>): Promise<Observed> {
    const fetchMock = stubOriginError(body)
    const { result } = renderHook(() => useGeneration())
    await act(async () => {
      await result.current.submit(TOPIC)
    })
    return {
      state: result.current.state,
      content: result.current.content,
      volumePages: result.current.volumePages,
      createdAt: result.current.createdAt,
      error: result.current.error,
      requests: requestLog(fetchMock),
      authorizationHeaders: authorizationHeaders(fetchMock),
    }
  }

  // The create never succeeded, so there is nothing to show and every result field must be null.
  // The single recorded request carrying the seeded session is what pins that the 500 is the
  // origin refusing — not the transport declining to send, and not a 401 replay path.
  function expectFailedWith(observed: Observed, error: string): void {
    expect(observed).toEqual({
      state: 'failed',
      content: null,
      volumePages: null,
      createdAt: null,
      error,
      requests: [CREATE_REQUEST],
      authorizationHeaders: [`Bearer ${ACCESS_TOKEN}`],
    })
  }

  // H9.4, `useGeneration.ts:140`. The origin's catch-all 500 body is measured and ENGLISH, so its
  // `message` must not be what a Russian UI shows — the caller's fallback and the status are. The
  // case below used to stub this same code with a hand-rolled RUSSIAN message, which is why the
  // English never showed up in any test.
  it("does not show the catch-all 500's English text when creating the generation", async () => {
    expectFailedWith(
      await submitAndObserve(ORIGIN_INTERNAL_ERROR_BODY),
      'Не удалось создать запрос (HTTP 500)',
    )
  })

  // An EXPLAINED 5xx keeps its text: the carve-out is keyed on the catch-all code, not the status.
  it("shows the origin's message when creating the generation hits an explained 5xx", async () => {
    expectFailedWith(
      await submitAndObserve(ORIGIN_PROVIDER_UNAVAILABLE_BODY),
      ORIGIN_PROVIDER_UNAVAILABLE_BODY.message,
    )
  })

  // No readable text — the status is the only fact left and must not be discarded.
  it('keeps the status visible when the 500 body carries no readable text', async () => {
    expectFailedWith(await submitAndObserve({}), 'Не удалось создать запрос (HTTP 500)')
  })
})
