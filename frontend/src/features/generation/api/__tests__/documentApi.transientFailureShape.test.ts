import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearSession, saveSession } from '../../../auth/utils/authSession'
import { REQUEST_TIMEOUT_MS } from '../../../../shared/api/httpClient'
import {
  ACCESS_TOKEN,
  ORIGIN_INTERNAL_ERROR_BODY,
  REFRESH_TOKEN,
  type FetchMock,
  captureRejection,
  expectClassifiableAsTransient,
  expectClassifiableAsTransientByIdentity,
  expectSingleSaveRequest,
  expectTransientButKnownNotToHaveLanded,
  isStillPending,
  saveUnderTest,
  serverError,
} from './documentApi.transientFailureShape.testSupport'

// H9.4 — the seam between what `saveDocument` REJECTS WITH and what the autosave retry policy can
// CLASSIFY. Everything the H9.3 retry branch and the H9.4 memory fix do is gated on
// `isTransientFailure(error)` / `mayHaveLandedServerSide(error)` at `useDocumentSave.ts:126`, and
// both predicates read `error.status` off the rejection. So the whole feature is only as real as
// this seam, and NOTHING in the repo pins it: every suite in the autosave family carries
// `vi.mock('../../api/documentApi')` and hands the hook a hand-rolled `{status: 5xx, body: {}}`,
// which stubs out the exact module boundary under test here. This file is the only place the two
// halves meet, so it deliberately mocks `fetch` — the REAL `httpClient` → `authorizedRequest` →
// `send` → `documentApi` chain runs, flattening and all.
//
// Sibling: `documentApi.conflict.test.ts` pins the OTHER thing `send` must preserve across the same
// boundary (409 → `VersionConflictError`). Weakening either leaves a caller matching on message
// text to recover.
//
// The rejection is asserted as a SHAPE, not just as a predicate outcome — see
// `expectHttpRejection` in the testSupport module for why.

describe('documentApi save rejection stays classifiable by the autosave retry policy', () => {
  beforeEach(() => {
    saveSession({ accessToken: ACCESS_TOKEN, refreshToken: REFRESH_TOKEN })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  // `mockImplementation`, deliberately NOT `mockResolvedValue`: the latter hands back ONE
  // already-constructed `Response` whose body stream is consumable once, so a second call gets a
  // drained object and `performRequest`'s `res.json().catch(() => ({}))` swallows the
  // `body used already` TypeError into `{}` — degrading a green that routed into `saveDocument`'s
  // 409 refetch-and-retry into a silently-wrong body instead of a failure. A fresh `Response`
  // per call keeps `expectSingleSaveRequest` the thing that catches an extra request.
  function stubFetchWith(status: number, body?: Record<string, unknown>): FetchMock {
    const fetchMock: FetchMock = vi.fn()
    fetchMock.mockImplementation(() => Promise.resolve(serverError(status, body)))
    vi.stubGlobal('fetch', fetchMock)
    return fetchMock
  }

  // 504 is the motivating status of the whole H9.4 unit: a proxy that gave up on an origin which
  // may already have committed. If it does not survive the boundary as an HttpError, no backoff is
  // ever scheduled and `mayHaveLandedServerSide` is never called — the memory fix is unreachable.
  it('keeps a 504 classifiable as transient', async () => {
    const fetchMock = stubFetchWith(504)

    const rejection = await captureRejection(saveUnderTest())

    expectClassifiableAsTransient(rejection, 504)
    expectSingleSaveRequest(fetchMock)
  })

  // 500 is the only 5xx this system actually emits (measured 2026-07-28,
  // `backend/adapters/rest/src/error_handling/exception_handlers.py:64-77`), so it is the case that
  // decides whether the retry branch runs in PRODUCTION rather than only in a fixture.
  // ...and it is the one case carrying the origin's REAL body rather than the `{}` a proxy leaves.
  // The other cases here are proxy-shaped answers where `{}` is truthful (an HTML 502 page makes
  // `res.json()` throw and `performRequest` substitutes `{}`); this one is the app's own handler,
  // and `{error_code, message}` is the field that decides whether the server's text can reach a
  // user at all once `send` stops flattening.
  it('keeps the origin catch-all 500 classifiable as transient, body and all', async () => {
    const fetchMock = stubFetchWith(500, ORIGIN_INTERNAL_ERROR_BODY)

    const rejection = await captureRejection(saveUnderTest())

    expectClassifiableAsTransient(rejection, 500, ORIGIN_INTERNAL_ERROR_BODY)
    expectSingleSaveRequest(fetchMock)
  })

  // 502 is the second proxy-shaped answer to the same question and shares the 504 branch. Cheap,
  // and it stops a carve-out written for the literal status 504 from passing.
  it('keeps a 502 classifiable as transient', async () => {
    const fetchMock = stubFetchWith(502)

    const rejection = await captureRejection(saveUnderTest())

    expectClassifiableAsTransient(rejection, 502)
    expectSingleSaveRequest(fetchMock)
  })

  // 503 is the DISCRIMINATING case: the sole 5xx where the two predicates disagree — retryable, but
  // the server answered "I did not take your write", so the dirty guard's memory survives it. Every
  // other case here takes the `true` arm of both, which a `mayHaveLandedServerSide` that was
  // `isTransientFailure` verbatim would satisfy.
  it('keeps a 503 transient while pinning that it did not land server-side', async () => {
    const fetchMock = stubFetchWith(503)

    const rejection = await captureRejection(saveUnderTest())

    expectTransientButKnownNotToHaveLanded(rejection, 503)
    expectSingleSaveRequest(fetchMock)
  })
})

// The type-carrying half of the same seam. `RequestTimeoutError` is not an HttpError — it has no
// status — so it survives (or not) on its IDENTITY, and `isTransientFailure`'s first line is an
// `instanceof` check. It is flattened by the same final `throw new Error(describeFailure(...))`,
// and the tell is that its message ('Request timed out') passes through `describeFailure`'s
// non-HttpError arm unchanged: the text looks right on a rejection whose type is gone.
//
// Fake timers, because the timeout is produced by `httpClient`'s real `withTimeout` racing a
// never-settling fetch — the same construction as `shared/api/__tests__/httpClient.timeout.test.ts`.
// Injecting a `RequestTimeoutError` from the fetch stub instead would test nothing: it would skip
// the transport that mints it.
describe('documentApi save rejection keeps the timeout type across the send boundary', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    saveSession({ accessToken: ACCESS_TOKEN, refreshToken: REFRESH_TOKEN })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('keeps a request timeout classifiable as transient', async () => {
    const fetchMock: FetchMock = vi.fn(() => new Promise<Response>(() => {}))
    vi.stubGlobal('fetch', fetchMock)

    const pending = captureRejection(saveUnderTest())
    // The bound must be a bound in BOTH directions. Without this the suite cannot tell the real
    // 25s timeout from a transport that gave up immediately, so a regression collapsing
    // REQUEST_TIMEOUT_MS toward zero — which would abort slow-but-valid generations — stays green.
    await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS - 1)
    expect(await isStillPending(pending)).toBe(true)
    await vi.advanceTimersByTimeAsync(1)

    expectClassifiableAsTransientByIdentity(await pending)
    expectSingleSaveRequest(fetchMock)
  })
})
