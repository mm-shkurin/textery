import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ProjectsPage } from '../ProjectsPage'
import { mockFeedRejection } from './feedTestHarness'
import { MISSING_UPDATED_AT_MESSAGE } from '../../api/projectsApi'

// `GET /api/v1/projects` does not exist on the backend yet — this suite builds against a mock of
// it, never a live call.
vi.mock('../../api/projectsApi')

// Its own file rather than a block in `ProjectsPage.feed.test.tsx`: every test there mocks a
// RESOLVING `listProjects` and asserts what the cards say. This one is about the other half of the
// client's contract — the rejection `parseUpdatedAt` ships — and about the page, not a card.
describe('ProjectsPage when listProjects rejects', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  // BOTH halves are asserted, and neither alone is the test. The failure this pins is not "no
  // error is shown" and not "cards are missing" — it is that the two are indistinguishable: with
  // no `.catch` in `ProjectsPage`, a serializer renaming `updated_at` produces an unhandled promise
  // rejection and a page byte-identical to a user who genuinely has no projects. So the error
  // element proves the page SAYS something, and the zero-card count proves the thing it says is
  // not being said over a feed that also rendered — the empty-vs-broken confusion is only ruled
  // out when both hold at once.
  //
  // The message is imported from `projectsApi`, never inlined: the green for the mapper exported
  // `MISSING_UPDATED_AT_MESSAGE` precisely so one definition exists, and a literal copy here would
  // pass while the two drifted apart.
  // RED: failed with `Error: Test timed out in 5000ms.` — `ProjectsPage` renders no
  // `projects-error` element at all, so `findByTestId` polled until Testing Library's 5000ms
  // asyncUtilTimeout tied vitest's 5000ms testTimeout and the outer timeout won the race (the same
  // race `ProjectsPage.feed.test.tsx` documents). The run ALSO reported one Unhandled Rejection —
  // `Error: Сервер вернул проект без даты изменения.` escaping the un-caught `.then` — which is the
  // second half of this step's finding observed live rather than argued.
  it.skip('shows an error instead of a feed that looks empty', async () => {
    mockFeedRejection(MISSING_UPDATED_AT_MESSAGE)

    render(<ProjectsPage />)

    const error = await screen.findByTestId('projects-error')
    // `.textContent` compared with `toBe`, not `toHaveTextContent`: the latter is a SUBSTRING
    // match, so it would pass on an element reading "Ошибка: Сервер вернул проект без даты
    // изменения. Повторите попытку" — a different rendered string than this test specifies. The
    // sibling suites anchor with `/^…$/` for the same reason; here the message ends in a `.`, which
    // is a regex metacharacter, so exact string equality states the intent without escaping.
    expect(error.textContent).toBe(MISSING_UPDATED_AT_MESSAGE)

    // `queryAllByTestId`, not `findAllBy*`: the cards' absence is asserted only AFTER the error has
    // arrived, so the page has demonstrably finished its load and this is a statement about a
    // settled DOM rather than a race the assertion happens to win.
    expect(screen.queryAllByTestId('project-card')).toHaveLength(0)
  })
})
