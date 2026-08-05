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
  vi.mocked(projectsApi.listProjects).mockRejectedValue(new Error(message))
}

// Called from inside a `describe`, never at file scope — the feed-rendering suite
// (`ProjectsPage.feed.test.tsx`) is deliberately left on the real clock, and a top-level pin would
// silently cover it. The instant stays at the call site rather than baked in here, because "older
// year" and "renders without a year" are both claims about a fixture's date RELATIVE to this now;
// a reader of the block has to see it. `setSystemTime` alone — not `useFakeTimers` — because the
// component resolves a mocked promise, and a fully faked timer queue would stall `findBy*`.
export function pinClockTo(instant: string) {
  beforeEach(() => {
    vi.setSystemTime(new Date(instant))
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })
}
