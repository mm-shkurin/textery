// Test support for `ManualEditor.autosaveRevertRepairsDivergence.test.tsx` — the scripted `fetch`
// and the request-assertion vocabulary for the one suite in the autosave family that does NOT mock
// `documentApi`. A plain .ts module: nothing here renders, and non-component exports on the
// component-rendering support file trip react(only-export-components).
import { expect, vi, type Mock } from 'vitest'
import { CREATED_DOCUMENT_ID } from './ManualEditor.autosave.testSupport'
import { SAVED_VERSION } from './ManualEditor.autosaveFixture'

export const ACCESS_TOKEN = 'access-1'
export const REFRESH_TOKEN = 'refresh-1'

// The versions the divergence runs through, each derived from the one before rather than written as
// bare numbers: they are only meaningful as a CHAIN — the server one ahead of what the client holds
// (the 504'd write that landed), the repair one past that, and a later save one past the repair.
// Retuning the fixture's baseline must move all of them together or the tuples assert a fiction.
export const DIVERGED_VERSION = SAVED_VERSION + 1
export const REPAIRED_VERSION = DIVERGED_VERSION + 1
export const RE_SAVED_VERSION = REPAIRED_VERSION + 1
export const FINAL_VERSION = RE_SAVED_VERSION + 1

// The response bodies the scripted `fetch` answers with. They live here rather than in the test
// class because they are transport infrastructure feeding `scriptFetch`'s script array, not part of
// the scenario narrative — the narrative is WHICH of them each call gets, which stays in the test.
export function ok(content: string, version: number): Response {
  return new Response(
    JSON.stringify({ document_id: CREATED_DOCUMENT_ID, status: 'draft', content, version }),
    { status: 200 },
  )
}

export function failure(status: number, body: Record<string, unknown> = {}): Response {
  return new Response(JSON.stringify(body), { status })
}

// Typed with the arguments `httpClient` actually passes, so a recorded call reads back as a
// `[url, init]` tuple without a cast (mirrors documentApi.transientFailureShape.testSupport).
export type FetchMock = Mock<(input: string, init: RequestInit) => Promise<Response>>

// A `fetch` that answers a fixed SEQUENCE, one factory per call. Factories rather than ready-made
// `Response` objects: a body stream is consumable once, and this suite's whole point is that
// several requests go out — a reused `Response` would surface as `performRequest`'s
// `res.json().catch(() => ({}))` silently substituting an empty body for the refetched version.
//
// An unscripted call FAILS rather than returning a default: this suite asserts an exact request
// count, and a permissive fallback would let an extra round trip pass as a body the test then
// blames on the wrong layer.
//
// It REJECTS rather than throwing synchronously. A synchronous throw out of `mockImplementation`
// unwinds inside the component's save loop, where the `.catch` treats it as a transport failure and
// `useAutosaveFailureFakeTimers` silences the console — an extra request would surface as a
// retry-shaped mystery, or as an unhandled rejection, instead of as a failed expectation. Rejecting
// puts it on the same path a real fetch error takes; the exact-count assertions are what fail.
export function scriptFetch(script: Array<() => Response>): FetchMock {
  let call = 0
  const fetchMock: FetchMock = vi.fn()
  fetchMock.mockImplementation(() => {
    const next = script[call]
    if (!next) {
      return Promise.reject(
        new Error(`unscripted fetch call #${call + 1} — the script has ${script.length} entries`),
      )
    }
    call += 1
    return Promise.resolve(next())
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

// The session token is asserted on every request, not just seeded: it is what pins that the REAL
// `authorizedRequest` layer ran rather than being bypassed by the fixture. Headers are asserted as
// the WHOLE object by each caller rather than by picking `Authorization` out of it, because their
// content is a branching fact — `httpClient` sends `Content-Type: application/json` only when there
// is a body (httpClient.ts:133), and a partial check pins neither branch.
const AUTH_HEADER = { Authorization: `Bearer ${ACCESS_TOKEN}` }

function expectRequest(fetchMock: FetchMock, nth: number, method: string): RequestInit {
  expect(
    fetchMock.mock.calls.length,
    `expected at least ${nth} fetch calls`,
  ).toBeGreaterThanOrEqual(nth)
  const [url, init] = fetchMock.mock.calls[nth - 1]
  expect({ url, method: init.method ?? 'GET' }).toEqual({
    url: `/api/v1/documents/${CREATED_DOCUMENT_ID}`,
    method,
  })
  return init
}

// One PUT, asserted as the CONTENT/VERSION tuple it carries — the pair is the claim. Asserting the
// content alone leaves a write at a stale version green, and the version alone leaves a repaired
// version carrying the wrong text green; this scenario can fail in both directions.
export function expectPut(
  fetchMock: FetchMock,
  nth: number,
  content: string,
  version: number,
): void {
  const init = expectRequest(fetchMock, nth, 'PUT')
  expect(init.headers).toEqual({ 'Content-Type': 'application/json', ...AUTH_HEADER })
  expect(JSON.parse(init.body as string)).toEqual({ content, version })
}

// The refetch half of `saveDocument`'s 409 recovery. Pinned as a request of its own because it is
// the step that DISCOVERS the divergence — a green that re-PUT at a guessed version instead of a
// fetched one would satisfy the PUT assertions on either side of it.
//
// The header set is pinned EXACTLY, with no `Content-Type`: its presence on a bodyless request is
// the tell that the client built this hop as a write rather than as the refetch it must be.
export function expectGet(fetchMock: FetchMock, nth: number): void {
  const init = expectRequest(fetchMock, nth, 'GET')
  expect(init.headers).toEqual({ ...AUTH_HEADER })
  expect(init.body).toBeUndefined()
}
