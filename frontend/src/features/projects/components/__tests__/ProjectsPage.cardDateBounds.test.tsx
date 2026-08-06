import { describe, expect, it, vi } from 'vitest'
import { screen, within } from '@testing-library/react'
import { mockFeed, pinClockTo, renderProjectsPage } from './feedTestHarness'
import { MAX_SENTINEL_DATE_PROJECT, MIN_SENTINEL_DATE_PROJECT } from './projectSentinelFixtures'

// `GET /api/v1/projects` does not exist on the backend yet — this suite builds against a mock of
// it, never a live call.
vi.mock('../../api/projectsApi')

// Its own file rather than a fourth block in `ProjectsPage.cardDate.test.tsx`: that file is at 198
// lines and the 200-line limit is hard. The seam is a real one — every test there pins a date whose
// SHAPE is wrong (unparseable, null, a number) or right (a genuine 1970). Both fixtures here are
// perfectly shaped ISO strings that parse into perfectly valid Dates, and are wrong only in VALUE.
describe('ProjectsPage card date for a project whose updatedAt is a backend sentinel', () => {
  // Pinned for the isolation `pinClockTo` also provides (`clearAllMocks` between the two tests
  // below), not because the assertions depend on the instant: year 1 and year 10000 differ from
  // every plausible now, so both fixtures take the year-showing branch against any clock. Stated
  // rather than left implicit, because the sibling file's blocks pin for the opposite reason and a
  // reader arriving from there will assume this one does too.
  pinClockTo('2026-08-03T12:00:00.000Z')

  // The arm that survives every guard `formatCardDate` ships. `typeof iso !== 'string'` passes it —
  // it IS a string. `Number.isNaN(date.getTime())` passes it — it IS a valid Date. Both shipped
  // guards ask about the SHAPE of the value the wire sent; a sentinel arrives in perfect shape and
  // means "no date", so the only thing that can reject it is a bounded plausible-year check on the
  // parsed result. `0001-01-01T00:00:00Z` is what a nullable timestamp column serializes to when it
  // is mapped through a non-nullable domain field — `LocalDate.MIN`, `datetime.min`,
  // `DateTime.MinValue` all land here.
  //
  // Anchored `/^—$/` and not `toHaveTextContent('—')`, for the reason the sibling file states: the
  // latter is a substring match and would pass on '— 1 января 1'.
  // RED: failed with `Expected /^—$/, Received: "1 января 1"`.
  it('renders a placeholder when updatedAt is the min-value sentinel, never year 1', async () => {
    mockFeed([MIN_SENTINEL_DATE_PROJECT], 1)

    renderProjectsPage()

    const card = await screen.findByTestId('project-card-document-23')

    expect(within(card).getByTestId('project-card-date')).toHaveTextContent(/^—$/)

    // Same anti-early-return pin every placeholder test in this suite carries: a green fix that
    // returns null from `ProjectCard` would satisfy the assertion above by rendering nothing, and a
    // sentinel timestamp must cost the user the date, not the project.
    expect(within(card).getByTestId('project-card-title')).toHaveTextContent(
      /^Проект с минимальной датой$/,
    )
  })

  // The other end, and a separate `it` for the reason the sibling file splits its own pairs: one
  // test stops at its first failing assertion, so folding both sentinels into one would leave this
  // arm UNREACHED while the min arm is red — and green would be handed one visible failure where
  // there are two. That matters more here than anywhere else in the suite, because the cheapest fix
  // for the test above is a lower bound alone (`year >= 1970`), which leaves this card rendering
  // '1 января 10000' and still passing. Split, the half-fix is impossible.
  //
  // This is also the arm with the larger blast radius: 1.4's «Недавние проекты» rail sorts on
  // `updated_at` descending, so one row carrying this sentinel pins itself to the top slot forever
  // and the user's real newest work never surfaces.
  // RED: failed with `Expected /^—$/, Received: "1 января 10000"`.
  it('renders a placeholder when updatedAt is the max-value sentinel, never year 10000', async () => {
    mockFeed([MAX_SENTINEL_DATE_PROJECT], 1)

    renderProjectsPage()

    const card = await screen.findByTestId('project-card-document-25')

    expect(within(card).getByTestId('project-card-date')).toHaveTextContent(/^—$/)

    // Same anti-early-return pin as its sibling, for the same reason.
    expect(within(card).getByTestId('project-card-title')).toHaveTextContent(
      /^Проект с максимальной датой$/,
    )
  })
})
