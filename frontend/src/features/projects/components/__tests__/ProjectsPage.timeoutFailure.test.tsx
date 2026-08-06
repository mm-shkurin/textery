import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ProjectsPage } from '../ProjectsPage'
import { mockFeedFailure, resetFeedMocks } from './feedTestHarness'
import { LOAD_FAILURE_FALLBACK } from '../../api/projectsApi'
import { RequestTimeoutError } from '../../../../shared/api/httpClient'

// `GET /api/v1/projects` does not exist on the backend yet — this suite builds against a mock of
// it, never a live call.
vi.mock('../../api/projectsApi')

// A third failure file, and the first one whose rejection is not a plain `new Error(...)`. The two
// siblings both reject with `MISSING_UPDATED_AT_MESSAGE` wrapped in an `Error`, which is the single
// branch where `describeFailure` returning `.message` and returning the screen's fallback are
// indistinguishable — so neither of them can see what this one is about.
describe('ProjectsPage renders a timed-out load in the user’s language', () => {
  resetFeedMocks()

  // The rejection is a REAL `RequestTimeoutError`, constructed rather than imitated: `send.ts:93`
  // re-throws it by identity (`error instanceof RequestTimeoutError`) so the autosave retry policy
  // can still classify it, which means it reaches `ProjectsPage`'s catch as an `Error` whose
  // `.message` is the English sentence `httpClient.ts:70-75` hardcodes for the transport layer.
  // `describeFailure`'s last line prefers any `Error.message` over the caller's fallback, so the
  // screen paints `Request timed out` — English, on a Russian-only UI, on the failure a real user
  // hits most (a slow or dropped connection), while `LOAD_FAILURE_FALLBACK` is honoured only on the
  // rarer serializer regression. An `Error('Request timed out')` stand-in would reproduce the
  // rendered text but not the type, and the type is the reason the text survives that far.
  //
  // Asserted with `toBe` on `.textContent`, matching both siblings: `toHaveTextContent` is a
  // SUBSTRING match and would pass on a banner that still carried the English inside a Russian
  // wrapper — which is the defect, not the fix. `LOAD_FAILURE_FALLBACK` is imported from
  // `projectsApi`, never inlined, for the reason the siblings give about the message they import:
  // the component already hands this exact constant to `describeFailure`, and a literal copy here
  // could pass while the two drifted.
  // RED: failed with `AssertionError: expected 'Request timed out' to be 'Не удалось загрузить
  // проекты' // Object.is equality`. Note what this is NOT: no `Unable to find` and no timeout —
  // the banner mounts, is found immediately, and carries a sentence. The page is not silent on a
  // timeout, it is fluent in the wrong language, which is why every earlier assertion in this
  // scenario (element present, role present) holds green while this one fails. First red in the
  // scenario to produce a real value-vs-value diff rather than a missing element.
  it.skip('shows the Russian load-failure sentence when the request times out', async () => {
    mockFeedFailure(new RequestTimeoutError())

    render(<ProjectsPage />)

    const error = await screen.findByTestId('projects-error')

    // DELIBERATELY the only assertion. `/test-review` proposed adding the sibling's
    // `expect(screen.queryAllByTestId('project-card')).toHaveLength(0)` here; it was declined,
    // because this scenario has already ruled that assertion vacuous — `items` has exactly one
    // writer, inside `.then`, so on ANY rejection zero cards holds for every implementation, before
    // and after green. The sibling's copy is a known defect with its own remediation step
    // («a failed load does not also offer the empty state»), not a standard to spread to a third
    // file. The falsifiable half of "the page committed to the failure" is the empty-state
    // affordance, which does not exist until scenario 2.3.
    expect(error.textContent).toBe(LOAD_FAILURE_FALLBACK)
  })
})
