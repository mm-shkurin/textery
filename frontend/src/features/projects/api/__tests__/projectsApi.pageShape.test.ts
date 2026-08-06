import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { listProjects } from '../projectsApi'
import { clearSession, saveSession } from '../../../auth/utils/authSession'
import { settle, stubFetchJson } from './projectsWireFixtures'

// Scenario 1.1 — the SHAPE of the feed page, at the mapper. The sibling
// `projectsApi.wireContract.test.ts` guards a field OF an item; this one guards the presence of the
// item list itself, which is the weaker input getting the worse rendering today.
//
// WHAT IS BROKEN. `projectsApi.ts:96` does `data.items.map(...)` with no shape check, and
// `httpClient.ts:167` deliberately turns an empty or unparseable SUCCESSFUL body into `{}`
// (`await res.json().catch(() => ({}))`). So a 204, an empty 200, or any body missing `items`
// throws a `TypeError` INSIDE `listProjects` — DOWNSTREAM of `send`, which means none of
// `send.ts`'s carve-outs ever see it and it reaches `ProjectsPage`'s catch as a real `Error`. The
// banner then paints `Cannot read properties of undefined (reading 'map')`: English, and an
// internal JS engine string, on a Russian-only screen. This feature spent two work units removing
// exactly that class of leak (`Request timed out`, `Failed to fetch`) from the transport arm while
// the mapper arm produced a worse one.
//
// THE CONTRACT, following the precedent `parseUpdatedAt` / `MISSING_UPDATED_AT_MESSAGE` already set
// in this file's production module: `listProjects` REJECTS the whole page with an exact, Russian,
// human-readable message. Not `items: []` — resolving empty makes a broken endpoint render
// identically to a user with no projects, which is the precise confusion this whole scenario exists
// to eliminate, and 2.3's empty state would then invite the user to create their first project on
// top of a server fault.
//
// GREEN OWES TWO THINGS, not one:
//   1. export this message constant from `projectsApi.ts` (the literal below is local ONLY because
//      RED may not touch production code; the `/refactor` after green replaces it with the import,
//      or the two definitions drift — same sequence as `MISSING_UPDATED_AT_MESSAGE`);
//   2. add that constant to `FEED_AUTHORED_MESSAGES` in `api/loadFailureMessages.ts`. Without it
//      the guard reaches `describeLoadFailure` as a plain `Error` whose message is not on the
//      allow-list and degrades to the generic `LOAD_FAILURE_FALLBACK` — safe, but this sentence
//      would then never reach the screen at all.
const EXPECTED_MESSAGE = 'Сервер вернул некорректный список проектов.'

describe('projectsApi page shape', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  // RED (verified unskipped): rejected with
  // `TypeError: Cannot read properties of undefined (reading 'map')` instead of an `Error` carrying
  // the Russian guard message. Enable by removing `.skip` in the paired green.
  it.skip('rejects a successful response carrying no items instead of throwing an engine message', async () => {
    // `{}` is what `httpClient.ts:167` hands the mapper for a 204, an empty 200 body, or a body
    // that fails to parse — not a hypothetical shape, the literal value that line produces.
    const fetchMock = stubFetchJson({})

    const settled = await settle(listProjects())

    // Exactly one call, to the feed path: without this the test would also pass if the guard
    // rejected before any request went out, or if a 401-renew-and-replay fired a second call.
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/projects')
    expect(settled).toEqual({ rejected: true, error: new Error(EXPECTED_MESSAGE) })
  })
})
