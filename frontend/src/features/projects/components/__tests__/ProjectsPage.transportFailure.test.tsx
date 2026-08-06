import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ProjectsPage } from '../ProjectsPage'
import { mockFeedFailure, resetFeedMocks } from './feedTestHarness'
import { LOAD_FAILURE_FALLBACK } from '../../api/projectsApi'

// `GET /api/v1/projects` does not exist on the backend yet — this suite builds against a mock of
// it, never a live call.
vi.mock('../../api/projectsApi')

// The transport failure `ProjectsPage.timeoutFailure` does NOT cover, and the one a real user hits
// far more often than a 25s deadline: a dropped connection, a failed DNS lookup, or an offline
// device. `fetch` rejects those with a bare `TypeError('Failed to fetch')` (Firefox:
// «NetworkError when attempting to fetch resource.») immediately — `REQUEST_TIMEOUT_MS` never
// elapses, so no `RequestTimeoutError` is ever constructed and `OPAQUE_TRANSPORT_FAILURES` cannot
// match it.
//
// Why the rejection here is a plain `Error`, where the timeout sibling constructs the REAL type:
// the two shapes reach the screen differently, and reproducing that faithfully is the whole point.
// `send.ts:93` re-throws a `RequestTimeoutError` BY IDENTITY, so the sibling's type survives to the
// component. A fetch-layer `TypeError` matches none of `send.ts`'s carve-outs — not
// `SessionExpiredError`, not the 409 code, not `RequestTimeoutError`, not `isHttpError` (a
// `TypeError` has no `status`) — so it falls to `send.ts:96`,
// `throw new Error(describeFailure(error, fallback))`. The type is DESTROYED one layer above the
// page, and `describeFailure`'s last line copies the message across. What `ProjectsPage`'s catch
// actually receives is therefore `new Error('Failed to fetch')` — a plain `Error`, not a
// `TypeError` — and that is what this rejects with. Rejecting with a `TypeError` here would be the
// unfaithful stand-in: it would test a shape the page can never see.
//
// This is why the defect cannot be closed by adding an entry to `OPAQUE_TRANSPORT_FAILURES`: there
// is no surviving type to list. The comment above that list reads as though the transport class is
// closed, and it is not.
describe('ProjectsPage renders a dropped connection in the user’s language', () => {
  resetFeedMocks()

  // The guard shape already established on two other screens and never carried to this one:
  // `LoginForm.networkError.test.tsx:80` and `ExportControl.error.test.tsx:101` both assert that
  // fetch's raw transport text does not reach the user. Asserted twice, deliberately, and the two
  // are not redundant: the `toBe` pins WHAT the banner says (a green that merely blanked the
  // sentence, or substituted some third English string, would satisfy non-disclosure alone), and
  // the `document.body` check pins that the English is nowhere on the PAGE — a green that fixed the
  // banner while leaking 'Failed to fetch' into a title attribute or a debug node would pass the
  // first assertion and still be the defect.
  //
  // `toBe` on `.textContent`, not `toHaveTextContent`, matching all three siblings: the latter is a
  // SUBSTRING match and would pass on a Russian wrapper that still carried the English inside it.
  // RED: failed with `AssertionError: expected 'Failed to fetch' to be 'Не удалось загрузить
  // проекты' // Object.is equality`, at the FIRST assertion — the second never ran, and would have
  // failed too. Same failure SHAPE as the timeout sibling and a different cause: there the English
  // survived because the type survived; here it survives because the type did not, so the two reds
  // that look alike cannot be closed by the same edit.
  it('shows the Russian load-failure sentence when the connection drops', async () => {
    mockFeedFailure(new Error('Failed to fetch'))

    render(<ProjectsPage />)

    const error = await screen.findByTestId('projects-error')

    expect(error.textContent).toBe(LOAD_FAILURE_FALLBACK)
    expect(document.body.textContent).not.toContain('Failed to fetch')
  })
})
