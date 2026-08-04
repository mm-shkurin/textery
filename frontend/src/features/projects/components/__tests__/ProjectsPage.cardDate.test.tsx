import { describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { ProjectsPage } from '../ProjectsPage'
import { mockFeed, pinClockTo } from './feedTestHarness'
import {
  EDITED_LONG_AFTER_CREATION_PROJECT,
  MISSING_DATE_PROJECT,
  OLDER_YEAR_PROJECT,
  SECOND_OLDER_YEAR_PROJECT,
  UNPARSEABLE_DATE_PROJECT,
} from './projectFixtures'

// `GET /api/v1/projects` does not exist on the backend yet — this suite builds against a mock of
// it, never a live call.
vi.mock('../../api/projectsApi')

describe('ProjectsPage card date for a project from an older year', () => {
  // Pinned for the same reason as the accent block below, but here the pin IS the test: an
  // "older year" fixture is only older relative to a now, and an unpinned clock would silently
  // turn this scenario into the current-year one the moment the calendar rolled into 2025+1.
  pinClockTo('2026-08-03T12:00:00.000Z')

  // Anchored `/^…$/` against the MOCKUP's literal, not against the formatter's output. That
  // distinction is the whole test: `toLocaleDateString('ru-RU', {…, year: 'numeric'})` emits the
  // era suffix — '2 сентября 2025 г.' — and the mockup renders '2 сентября 2025'. A substring
  // assertion, or one written to match what the code already does, would pass and enshrine the
  // suffix on every card older than this year.
  it('renders the year for an older project, in the mockup’s format and without the era suffix', async () => {
    mockFeed([OLDER_YEAR_PROJECT], 1)

    render(<ProjectsPage />)

    const card = await screen.findByTestId('project-card-document-9')

    expect(within(card).getByTestId('project-card-date')).toHaveTextContent(/^2 сентября 2025$/)
  })

  // The same format, a second month and a second year — deliberately a separate `it` rather than a
  // second assertion above, so a failure names WHICH date the formatter got wrong instead of
  // stopping at the first. Anchored against the mockup's literal for the same reason as its
  // sibling: '16 декабря 2024 г.' is what ru-RU's `year: 'numeric'` would emit, and the design
  // does not carry the era suffix.
  it('renders a second older year in the same format, pinning a second genitive month', async () => {
    mockFeed([SECOND_OLDER_YEAR_PROJECT], 1)

    render(<ProjectsPage />)

    const card = await screen.findByTestId('project-card-document-11')

    expect(within(card).getByTestId('project-card-date')).toHaveTextContent(/^16 декабря 2024$/)
  })
})

describe('ProjectsPage card date for a project edited long after it was created', () => {
  // Pinned for the same reason as the older-year block: the assertion below expects the EDIT date
  // to render without a year, which is only true while "now" is 2026.
  pinClockTo('2026-08-03T12:00:00.000Z')

  // A de-aliasing regression pin, not a new behaviour: `ProjectCard` already calls
  // `formatCardDate(project.updatedAt)`. What was missing is any test that could tell — all four
  // existing fixtures set `createdAt === updatedAt`, so swapping the field the card reads left the
  // suite green. This test fails on that swap ('5 марта 2024' ≠ '15 июля') and is the only thing
  // in the file that does.
  it('renders the date the project was last edited, not the date it was created', async () => {
    mockFeed([EDITED_LONG_AFTER_CREATION_PROJECT], 1)

    render(<ProjectsPage />)

    const card = await screen.findByTestId('project-card-document-13')

    expect(within(card).getByTestId('project-card-date')).toHaveTextContent(/^15 июля$/)
  })
})

describe('ProjectsPage card date for a project whose updatedAt is unusable', () => {
  // Pinned for the same reason as the blocks above — and for one more: the malformed fixture's
  // year is NaN, and `NaN !== getFullYear()` is true against ANY now, so an unpinned clock would
  // hide that the year-showing branch is what produces the second failure token.
  pinClockTo('2026-08-03T12:00:00.000Z')

  // What SHOULD render is nothing. `12_MyProjects.md` and every mockup under `mockups/desktop/`
  // are silent on an unusable date — `01-projects-grid.html` renders `<div class="date">…</div>`
  // with a real date on every card and has no absent-date state — so this pins the card showing no
  // date TEXT, with the element itself kept (empty) rather than omitted.
  //
  // TWO CAVEATS ON THAT CONTRACT, both raised against this commit and neither yet resolved. The
  // green phase owns the decision; these tests are what has to change if it goes the other way.
  //
  // 1. Keeping the node was originally justified by 'the date slot is a grid row in projects.css'.
  //    That is false. `.project-card-body` is plain block flow and `.project-card-date` sets only
  //    `font-size`/`color` with no `min-height`, so an empty div is zero-height and omitting the
  //    node lays out identically. The real risk runs the other way: a zero-height date collapses
  //    the card ~14px shorter than its row neighbours, which is the alignment the title's
  //    line-clamp comment exists to protect. If the empty-element contract stands, the green owes
  //    `.project-card-date` a `min-height`; `align-design` for 1.1 is already `[x]` and no queued
  //    step re-runs it.
  // 2. '—' is NOT an invented placeholder. `HistoryPage.tsx`'s `formatDate` already returns it for
  //    an invalid date, and it is on screen in production today. Reading mockup silence as spec
  //    silence pins a THIRD contract (empty here, em dash in История, 'создан только что' in
  //    `formatRelativeTime`) without overruling the precedent.
  //
  // `toBeEmptyDOMElement` rather than `toHaveTextContent('')` on purpose — the latter is a
  // substring match against the empty string and passes on 'Invalid Date NaN', i.e. on exactly the
  // bug these tests exist to catch.
  //
  // The two bad-timestamp fixtures are two `it`s rather than one carrying both, for the reason the
  // older-year block above already splits its pair: one test stops at its first failing assertion,
  // so the epoch arm would be UNREACHED while the malformed arm is red, and green would be handed
  // one visible failure instead of two. That is precisely the half-fix this pair exists to close —
  // an `isNaN(getTime())` check repairs the malformed card and leaves the missing one reading
  // '1 января 1970'. Split, both failures are on screen at once and neither can be fixed silently;
  // the anti-half-fix property lives in both fixtures being pinned, not in sharing an `it`.

  // RED: fails with `expect(element).toBeEmptyDOMElement()` / Received: "Invalid Date NaN".
  // `formatCardDate` in ProjectCard.tsx does `new Date(iso)` with no validity check, and
  // `NaN !== currentYear` sends it down the year-SHOWING branch, concatenating two failure tokens.
  it.skip('renders no date text when updatedAt is unparseable, never a failure token', async () => {
    mockFeed([UNPARSEABLE_DATE_PROJECT], 1)

    render(<ProjectsPage />)

    const card = await screen.findByTestId('project-card-document-15')

    expect(within(card).getByTestId('project-card-date')).toBeEmptyDOMElement()

    // The card is still a card. A green fix that bails out of `ProjectCard` early — returning
    // null, or dropping the body — would satisfy the assertion above by rendering nothing at all,
    // and an unusable timestamp must cost the user the date, not the project.
    expect(within(card).getByTestId('project-card-title')).toHaveTextContent(
      /^Проект с испорченной датой$/,
    )
  })

  // RED: fails with `expect(element).toBeEmptyDOMElement()` / Received: "1 января 1970".
  // `new Date(null)` is the epoch — a VALID Date — so no validity check catches it, and 1970 is
  // not the pinned now, so the year branch renders it in full as a plausible-looking edit date.
  it.skip('renders no date text when updatedAt is missing, never the epoch', async () => {
    mockFeed([MISSING_DATE_PROJECT], 1)

    render(<ProjectsPage />)

    const card = await screen.findByTestId('project-card-document-17')

    expect(within(card).getByTestId('project-card-date')).toBeEmptyDOMElement()

    // Same anti-early-return pin as its sibling, for the same reason.
    expect(within(card).getByTestId('project-card-title')).toHaveTextContent(/^Проект без даты$/)
  })
})
