import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { listProjects } from '../projectsApi'
import { clearSession, saveSession } from '../../../auth/utils/authSession'
import { PROJECT_WIRE_WITHOUT_UPDATED_AT, stubFetchJson } from './projectsWireFixtures'

// Scenario 1.1 — the wire contract of the «Мои проекты» feed, at the mapper.
//
// WHY THIS EXISTS, and why it is not a card test. `formatCardDate` now renders `—` for any
// unusable date, which is right for one row whose date genuinely cannot be shown. It is wrong as
// the answer to a BROKEN ENDPOINT: `projects_schemas.yaml` declares `updated_at` required, so if
// the real endpoint lands with `updatedAt`, omits the field on the `generation` arm, or nests it,
// `projectsApi.ts` maps `undefined` and EVERY card renders `—` identically. That looks deliberate
// — it is the same glyph a legitimately unusable row shows — and would sit in production
// unnoticed. Before the em-dash landed the same break rendered `Invalid Date NaN`: wrong, but
// loud. The guard belongs where the contract is read, not where it is painted.
//
// FAIL-CLOSED CONTRACT, mirroring `documentApi`'s `parseVersion` (the codebase's only other
// required-wire-field guard): a required field that is absent is not a value to map, it is a
// broken response, and the whole call REJECTS with an Error carrying an exact, human-readable
// message — never resolves with `updatedAt: undefined`, and never falls back to a differently
// named key. Rejecting the page rather than dropping the row is deliberate: a serializer that
// omits a required field on one item is broken for all of them, and a silently short page hides
// that just as well as an em dash does. The fixture keeps every other field valid by deriving
// itself from `PROJECT_WIRE`, so nothing but the missing required key can be what fails; a mapper
// that "helpfully" read the camelCase key would resolve, and that is a defect — guessing at an
// undeclared contract is how a client stops noticing that the server changed.
//
// The expected message is a literal here only because RED may not touch production. GREEN exports
// it from `projectsApi.ts` (as `INVALID_VERSION_MESSAGE` is exported from `documentApi.ts`) and
// the refactor that follows replaces this literal with that import — one definition, no drift.
const EXPECTED_MESSAGE = 'Сервер вернул проект без даты изменения.'

type Settled = { rejected: false; value: unknown } | { rejected: true; error: unknown }

// Capture the settlement rather than `.rejects.toThrow()`: that would pass on ANY thrown value,
// including the generic 'Не удалось загрузить проекты' transport fallback — the one outcome this
// test most needs to tell apart from a real contract guard. Comparing the whole settlement in one
// `toEqual` then pins outcome, error type and message together: an `Error` and a plain object
// carrying the same `message` are not equal, and neither is a different message.
async function settle(promise: Promise<unknown>): Promise<Settled> {
  return promise.then(
    (value) => ({ rejected: false as const, value }),
    (error: unknown) => ({ rejected: true as const, error }),
  )
}

describe('projectsApi wire contract', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  it('rejects a project whose required updated_at is absent instead of mapping undefined', async () => {
    const fetchMock = stubFetchJson({
      items: [PROJECT_WIRE_WITHOUT_UPDATED_AT],
      total: 1,
      page: 1,
      limit: 20,
    })

    const settled = await settle(listProjects())

    // Exactly one call, to the feed path: without this the test would also pass if the guard
    // rejected before any request went out, or if a 401-renew-and-replay fired a second call —
    // neither of which is «the mapper refused a broken item». The request's full shape (method,
    // headers, absent body) is pinned by `projectsApi.test.ts`; only what this claim rests on is
    // re-asserted here.
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/projects')
    expect(settled).toEqual({ rejected: true, error: new Error(EXPECTED_MESSAGE) })
  })
})
