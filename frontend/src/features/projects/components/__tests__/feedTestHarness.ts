import { afterEach, beforeEach, vi } from 'vitest'
import * as projectsApi from '../../api/projectsApi'
import type { ProjectSummary } from '../../api/projectsApi'

// Callers must still declare `vi.mock('../../api/projectsApi')` in their own test file: the mock
// registry is per test file, and this module only reaches for whatever that file already faked.

// `total` is passed, never derived from `items.length` — the two differ the moment paging enters
// (test 3.x), and a helper that computes it cannot express a wrong-total bug.
export function mockFeed(items: ProjectSummary[], total: number) {
  vi.mocked(projectsApi.listProjects).mockResolvedValue({
    items,
    total,
    page: 1,
    limit: 20,
  })
}

// The other half of the contract `listProjects` actually has: it REJECTS on a broken wire body
// (`MISSING_UPDATED_AT_MESSAGE`), and every caller of `mockFeed` above only ever exercises the
// resolving half. Takes the message rather than an Error so the call site reads as the failure it
// is naming, and so the caller passes the exported constant instead of a drifting inline copy.
export function mockFeedRejection(message: string) {
  mockFeedFailure(new Error(message))
}

// The rejection `mockFeedRejection` structurally cannot express. `send.ts:93` re-throws a
// `RequestTimeoutError` and any 5xx `HttpError` WITH THEIR TYPE INTACT — a plain `new Error(msg)` is
// the one shape where every branch of `describeFailure` collapses to the same output, so a suite
// that can only produce it can never see the branches the divergence was written for. Takes
// `unknown`, not `Error`: a bare `HttpError` is an object literal (`httpClient.ts:141`) and is not
// an `Error` at all, which is precisely the distinction under test.
export function mockFeedFailure(failure: unknown) {
  vi.mocked(projectsApi.listProjects).mockRejectedValue(failure)
}

// The teardown every suite in this directory needs and three of them hand-rolled byte-identically
// (`ProjectsPage.feed`, `.loadFailure`, `.errorAnnounced`), while `pinClockTo` below already owned
// a fourth copy — so the one piece of per-suite infrastructure the harness did not expose was the
// one nobody could avoid writing. Called from inside a `describe` for the same reason `pinClockTo`
// is: registering `afterEach` at file scope would attach it to every block in the file, including
// any future block that deliberately keeps a mock across cases.
//
// `clearAllMocks`, not `resetAllMocks`: the suites mock `projectsApi` as a MODULE
// (`vi.mock('../../api/projectsApi')`), and reset would strip the auto-mock's implementations, not
// merely the recorded calls — every `mockFeed*` call would then have to re-establish more than the
// return value it means to state.
export function resetFeedMocks() {
  afterEach(() => {
    vi.clearAllMocks()
  })
}

// Called from inside a `describe`, never at file scope — the feed-rendering suite
// (`ProjectsPage.feed.test.tsx`) is deliberately left on the real clock, and a top-level pin would
// silently cover it. The instant stays at the call site rather than baked in here, because "older
// year" and "renders without a year" are both claims about a fixture's date RELATIVE to this now;
// a reader of the block has to see it. `setSystemTime` alone — not `useFakeTimers` — because the
// component resolves a mocked promise, and a fully faked timer queue would stall `findBy*`.
export function pinClockTo(instant: string) {
  // Delegated rather than repeated: the mock teardown this used to inline is the same teardown
  // `resetFeedMocks` states, and the two callers that pin the clock (`.accent`, `.cardDateBounds`)
  // document that they rely on it for isolation. Order between the two hooks is immaterial —
  // restoring the clock and clearing recorded calls touch nothing in common.
  resetFeedMocks()

  beforeEach(() => {
    vi.setSystemTime(new Date(instant))
  })

  afterEach(() => {
    vi.useRealTimers()
  })
}
