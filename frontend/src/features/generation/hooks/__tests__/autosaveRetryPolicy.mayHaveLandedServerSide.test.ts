import { describe, expect, it } from 'vitest'
import { type HttpError, RequestTimeoutError } from '../../../../shared/api/httpClient'
import { SessionExpiredError } from '../../../auth/api/authorizedRequest'
import { isTransientFailure, mayHaveLandedServerSide } from '../autosaveRetryPolicy'

// Scenario H9.4 — the axis the autosave dirty guard turns on, pinned as ONE named predicate.
//
// The guard's memory ("the server holds this content", recorded when a save was confirmed) is only
// safe to keep across a failure that PROVABLY did not land. Two failures that both retry can sit on
// opposite sides of that line, so `isTransientFailure` cannot answer it:
//   - 503 Service Unavailable — the server ANSWERED, and its answer is that it did not apply the
//     write. The memory is still exactly true, so suppressing a redundant re-PUT is correct.
//   - RequestTimeoutError — a purely CLIENT-side deadline: httpClient races the request against its
//     own timer and rejects when the timer wins (httpClient.ts:89-99), whether or not the transport
//     ever aborted and whether or not the server went on to commit. Server content is UNKNOWN.
//   - 504 / 502 — a proxy gave up on an origin that MAY have committed. Unknown for the same reason
//     a client deadline is, and `isTransientFailure`'s `status >= 500` puts them on the wrong side.
//
// Getting 504/502 wrong is not a lost retry, it is a silent divergence: the revert is suppressed,
// no PUT is issued, the badge reads «Сохранено» over a server holding the abandoned edit.
//
// Real error values, never hand-rolled shapes: `isHttpError` narrows structurally, so a fixture that
// drifted out of the production taxonomy would take the fall-through branch and this suite would
// pass for entirely the wrong reason.
const GATEWAY_TIMEOUT: HttpError = { status: 504, body: {} }
const BAD_GATEWAY: HttpError = { status: 502, body: {} }
const DEFINITE_SERVER_REJECTION: HttpError = { status: 503, body: {} }
const BAD_REQUEST: HttpError = { status: 400, body: {} }

// The 5xx range is a RANGE, not the enumeration {502, 504}. 503 is the sole carve-out because it is
// the only 5xx that answers the question — "unavailable, I did not take your write". Every other 5xx
// is a server that had the request in hand when it failed, and a failure after the commit but before
// the response is indistinguishable from one before it: 500 fires from a post-commit hook exactly as
// readily as from a rejected transaction. So the default across the range is UNKNOWN, and these two
// pin that it is a default rather than a lookup table — without them a bare
// `status === 504 || status === 502` allowlist satisfies this suite (verified by mutation).
const INTERNAL_SERVER_ERROR: HttpError = { status: 500, body: {} }
const UNCATALOGUED_SERVER_ERROR: HttpError = { status: 599, body: {} }
// The bottom edge of that range, adjacent to 500 on the 4xx side. 429 is the tempting one: it is the
// retry-shaped 4xx, and a green that keyed on "would we retry this?" rather than on the status floor
// would drag it across. A rate limiter refusing a request never applied it.
const TOO_MANY_REQUESTS: HttpError = { status: 429, body: {} }
const EDGE_BELOW_RANGE: HttpError = { status: 499, body: {} }

describe('mayHaveLandedServerSide — did the failure leave the server content unknown? (H9.4)', () => {
  it('is true for a client-side deadline: giving up waiting never unsends the request', () => {
    expect(mayHaveLandedServerSide(new RequestTimeoutError())).toBe(true)
  })

  it('is true for 504 — a proxy timeout over an origin that may have committed', () => {
    expect(mayHaveLandedServerSide(GATEWAY_TIMEOUT)).toBe(true)
  })

  it('is true for 502 — the origin answered unusably, not "did not apply"', () => {
    expect(mayHaveLandedServerSide(BAD_GATEWAY)).toBe(true)
  })

  it('is true for 500 — the server held the request when it failed, on either side of the commit', () => {
    expect(mayHaveLandedServerSide(INTERNAL_SERVER_ERROR)).toBe(true)
  })

  it('is true across the rest of the 5xx range — unknown is the default, not an enumeration', () => {
    expect(mayHaveLandedServerSide(UNCATALOGUED_SERVER_ERROR)).toBe(true)
  })

  it('is false for 503 — a definite server answer that the write did not apply', () => {
    // Both sides of the axis are transient, which is precisely why a second predicate is needed:
    // the retry question and the "is the memory still true" question are not the same question.
    expect(isTransientFailure(DEFINITE_SERVER_REJECTION)).toBe(true)
    expect(isTransientFailure(new RequestTimeoutError())).toBe(true)
    expect(mayHaveLandedServerSide(DEFINITE_SERVER_REJECTION)).toBe(false)
  })

  it('is false below the 5xx floor — a refusal to accept is not an unknown', () => {
    // 499 and 500 are adjacent, so the pair fixes exactly where the range opens. 429 fixes that the
    // edge is the STATUS floor and not "anything worth retrying".
    expect(mayHaveLandedServerSide(EDGE_BELOW_RANGE)).toBe(false)
    expect(mayHaveLandedServerSide(TOO_MANY_REQUESTS)).toBe(false)
  })

  it('is false for a non-transient failure — nothing was accepted', () => {
    // SessionExpiredError is thrown by authorizedRequest BEFORE any request goes out when no token
    // is held, so it also pins the default for a rejection that is not an HttpError at all: false.
    // A predicate that opened up for "anything unrecognised" would read a signed-out user as a
    // possible write and suppress the revert.
    expect(mayHaveLandedServerSide(new SessionExpiredError())).toBe(false)
    expect(mayHaveLandedServerSide(BAD_REQUEST)).toBe(false)
  })
})
