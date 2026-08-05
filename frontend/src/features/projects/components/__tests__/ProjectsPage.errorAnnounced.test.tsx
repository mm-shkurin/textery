import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ProjectsPage } from '../ProjectsPage'
import { mockFeedRejection, resetFeedMocks } from './feedTestHarness'
import { MISSING_UPDATED_AT_MESSAGE } from '../../api/projectsApi'

// `GET /api/v1/projects` does not exist on the backend yet — this suite builds against a mock of
// it, never a live call.
vi.mock('../../api/projectsApi')

// A separate file from `ProjectsPage.loadFailure.test.tsx` on purpose. That suite asks whether the
// page SAYS anything when the load breaks, and reaches the banner by `data-testid` — a hook only a
// test has. This one asks whether the thing it says is DELIVERED, and so it may only reach the
// banner the way assistive technology does: by role. Reaching it by testid here would make the two
// tests the same test written twice, and neither would pin the announcement.
describe('ProjectsPage error surface when listProjects rejects', () => {
  resetFeedMocks()

  // Queried with `findByRole('alert')` and never with `findByTestId`: a `<p data-testid=
  // "projects-error">` satisfies the sibling test exactly while carrying no live region, and a
  // screen-reader user then gets silence — a feed that never populates, indistinguishable from an
  // account with no projects, which is the precise confusion this scenario exists to kill. Every
  // other error surface in this codebase already announces (`LoginForm.tsx:84`, `:93`,
  // `OAuthErrorBanner.tsx:44`, `VerifyCodeForm.tsx:130`), so the feed being the one that does not
  // is an inconsistency as much as a defect.
  //
  // The text is asserted on the SAME node the role query returned, not on a separately-queried
  // one: an announcement on an empty live region next to the visible sentence would be a role in
  // the right place and no words in it. `MISSING_UPDATED_AT_MESSAGE` is imported rather than
  // inlined for the reason the sibling file gives — one definition of the message, so a literal
  // copy cannot pass while the two drift.
  // RED: failed with `Error: Test timed out in 5000ms.` — `ProjectsPage` renders the failure as a
  // `<p className="projects-error" data-testid="projects-error">`, and `<p>` carries no implicit
  // `alert` role, so `findByRole('alert')` polled the full 5000ms `asyncUtilTimeout` (setup.ts:17),
  // which ties vitest's 5000ms `testTimeout` — the outer timeout won the race and the test never
  // reached the `.textContent` assertion. Note what did NOT appear: no unhandled rejection, because
  // the `.catch` from the previous green already swallows it. The page shows the sentence; it just
  // does not say it.
  it('announces the load failure through a live region, not only on screen', async () => {
    mockFeedRejection(MISSING_UPDATED_AT_MESSAGE)

    render(<ProjectsPage />)

    const alert = await screen.findByRole('alert')

    expect(alert.textContent).toBe(MISSING_UPDATED_AT_MESSAGE)
  })
})
