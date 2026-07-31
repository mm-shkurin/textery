import { afterEach, beforeEach, describe, it, vi } from 'vitest'
import {
  ORIGIN_INTERNAL_ERROR_BODY,
  ORIGIN_PROVIDER_UNAVAILABLE_BODY,
} from '../../../../shared/api/__tests__/originErrorBodies'
import { resetOriginStubs, seedSession } from '../../../../shared/api/__tests__/originStubs'
import { driveUntilItGivesUp, expectGaveUpWith } from './useGeneration.pollServerError.testSupport'

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
// and lets `httpClient` → `send` → `generationApi` run for real. The scripting, the fake-timer
// drive and the give-up vocabulary live in the sibling `.testSupport.ts`.
describe('useGeneration — a poll that gives up on a 5xx says which status it gave up on', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    seedSession()
  })

  afterEach(() => {
    resetOriginStubs()
    vi.useRealTimers()
  })

  // H9.4, `useGeneration.ts:101`. The origin's catch-all 500 body is measured and ENGLISH, so the
  // give-up message must be the caller's Russian fallback plus the status — not the server's
  // sentence. This case previously stubbed the same code with a hand-rolled Russian message, which
  // is precisely how the English stayed invisible to the suite.
  it("does not show the catch-all 500's English text when the poll gives up", async () => {
    expectGaveUpWith(
      await driveUntilItGivesUp(ORIGIN_INTERNAL_ERROR_BODY),
      'Ошибка сети (HTTP 500)',
    )
  })

  // An EXPLAINED 5xx keeps its text: the carve-out is keyed on the catch-all code, not the status.
  it("shows the origin's message when the status endpoint fails with an explained 5xx", async () => {
    expectGaveUpWith(
      await driveUntilItGivesUp(ORIGIN_PROVIDER_UNAVAILABLE_BODY),
      ORIGIN_PROVIDER_UNAVAILABLE_BODY.message,
    )
  })

  // No readable text in the body — a proxy's own error page, or an origin that answered with none.
  // The status is then the only fact left, and it is the whole reason this catch stopped reading
  // `.message`: an `HttpError` is a bare object literal, so `.message` is `undefined` there and the
  // user would be told «Ошибка сети» with nothing to quote.
  it('keeps the status visible when the failing status check carries no readable text', async () => {
    expectGaveUpWith(await driveUntilItGivesUp({}), 'Ошибка сети (HTTP 500)')
  })
})
