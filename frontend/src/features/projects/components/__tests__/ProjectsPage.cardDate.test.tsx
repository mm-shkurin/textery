import { describe, expect, it, vi } from 'vitest'
import { screen, within } from '@testing-library/react'
import { mockFeed, pinClockTo, renderProjectsPage } from './feedTestHarness'
import {
  EDITED_LONG_AFTER_CREATION_PROJECT,
  EPOCH_DATE_PROJECT,
  MISSING_DATE_PROJECT,
  NUMERIC_DATE_PROJECT,
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

    renderProjectsPage()

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

    renderProjectsPage()

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

    renderProjectsPage()

    const card = await screen.findByTestId('project-card-document-13')

    expect(within(card).getByTestId('project-card-date')).toHaveTextContent(/^15 июля$/)
  })
})

describe('ProjectsPage card date for a project whose updatedAt is unusable', () => {
  // Pinned for the same reason as the blocks above — and for one more: the malformed fixture's
  // year is NaN, and `NaN !== getFullYear()` is true against ANY now, so an unpinned clock would
  // hide that the year-showing branch is what produces the second failure token.
  pinClockTo('2026-08-03T12:00:00.000Z')

  // What SHOULD render is an em dash. `12_MyProjects.md` and every mockup under `mockups/desktop/`
  // are silent on an unusable date — `01-projects-grid.html` renders `<div class="date">…</div>`
  // with a real date on every card and has no absent-date state — and the red phase read that
  // silence as the spec's silence, pinning an empty element. The user overruled it on review:
  // `HistoryPage.tsx`'s `formatDate` already returns '—' for an invalid date and is on screen in
  // production today, so an empty element here would be a THIRD contract for the same condition
  // (empty here, em dash in История, 'создан только что' in `formatRelativeTime`). These two
  // assertions were rewritten to '—' in green as the recorded resolution of that finding. The em
  // dash also occupies a line, which dissolves the collapsed-card-height risk the empty contract
  // carried.
  //
  // Anchored `/^—$/` rather than `toHaveTextContent('—')` on purpose — the latter is a substring
  // match and would pass on '— Invalid Date NaN', i.e. on exactly the bug these tests catch.
  //
  // The two bad-timestamp fixtures are two `it`s rather than one carrying both, for the reason the
  // older-year block above already splits its pair: one test stops at its first failing assertion,
  // so the epoch arm would be UNREACHED while the malformed arm is red, and green would be handed
  // one visible failure instead of two. That is precisely the half-fix this pair exists to close —
  // an `isNaN(getTime())` check repairs the malformed card and leaves the missing one reading
  // '1 января 1970'. Split, both failures are on screen at once and neither can be fixed silently;
  // the anti-half-fix property lives in both fixtures being pinned, not in sharing an `it`.

  // RED: failed with Received: "Invalid Date NaN". `formatCardDate` in ProjectCard.tsx did
  // `new Date(iso)` with no validity check, and `NaN !== currentYear` sent it down the
  // year-SHOWING branch, concatenating two failure tokens.
  it('renders a placeholder when updatedAt is unparseable, never a failure token', async () => {
    mockFeed([UNPARSEABLE_DATE_PROJECT], 1)

    renderProjectsPage()

    const card = await screen.findByTestId('project-card-document-15')

    expect(within(card).getByTestId('project-card-date')).toHaveTextContent(/^—$/)

    // The card is still a card. A green fix that bails out of `ProjectCard` early — returning
    // null, or dropping the body — would satisfy the assertion above by rendering nothing at all,
    // and an unusable timestamp must cost the user the date, not the project.
    expect(within(card).getByTestId('project-card-title')).toHaveTextContent(
      /^Проект с испорченной датой$/,
    )
  })

  // RED: failed with Received: "1 января 1970". `new Date(null)` is the epoch — a VALID Date — so
  // no validity check catches it, and 1970 is not the pinned now, so the year branch rendered it
  // in full as a plausible-looking edit date. Only an INPUT guard closes this arm.
  it('renders a placeholder when updatedAt is missing, never the epoch', async () => {
    mockFeed([MISSING_DATE_PROJECT], 1)

    renderProjectsPage()

    const card = await screen.findByTestId('project-card-document-17')

    expect(within(card).getByTestId('project-card-date')).toHaveTextContent(/^—$/)

    // Same anti-early-return pin as its sibling, for the same reason.
    expect(within(card).getByTestId('project-card-title')).toHaveTextContent(/^Проект без даты$/)
  })

  // The third shape of a bad `updated_at`, and the one the guard was written wide enough to catch
  // without ever being asked to: epoch millis as a NUMBER. `new Date(1755000000)` is valid,
  // non-NaN and non-null, and reads '21 января 1970' — so neither the malformed fixture's check
  // nor the missing one's would stop it. The green above wrote `typeof iso !== 'string'` when its
  // two tests only forced `iso == null`; this test is what makes that line load-bearing instead of
  // generous. Narrowing it back to a null check is now a failure rather than a passing
  // simplification.
  //
  // RED: passes on arrival — `typeof iso !== 'string'` already catches it. A regression pin on an
  // untested arm, not a red state.
  it('renders a placeholder when updatedAt arrives as epoch millis, never a 1970 date', async () => {
    mockFeed([NUMERIC_DATE_PROJECT], 1)

    renderProjectsPage()

    const card = await screen.findByTestId('project-card-document-19')

    expect(within(card).getByTestId('project-card-date')).toHaveTextContent(/^—$/)

    // Same anti-early-return pin as its two siblings, for the same reason.
    expect(within(card).getByTestId('project-card-title')).toHaveTextContent(
      /^Проект с числовой датой$/,
    )
  })
})

// Its own block rather than a fourth `it` in the unusable-date one above, because it is the exact
// opposite claim: this timestamp is USABLE. Filing it under "unusable" would put a test asserting a
// real rendered date under a heading promising a placeholder, and the next reader would have to
// read the body to find out which. The describe name is the only summary most failures get.
describe('ProjectsPage card date for a project genuinely edited on the epoch', () => {
  // Pinned for the same reason as every block above, and one specific to this one: the assertion
  // expects the year to be SHOWN, which is a claim about 1970 differing from now.
  pinClockTo('2026-08-03T12:00:00.000Z')

  // The converse hole of the two placeholder tests above, and the only test in this file that
  // fails on it. Every guard those two forced is a guard on the INPUT — the shape of the value the
  // wire sent. The cheapest way to satisfy both while writing something else entirely is
  // `|| date.getTime() === 0` on the validity check: it passes all nine tests that existed before
  // this one, because no fixture had ever been a real 1970 date, and it silently blanks the card of
  // any user whose work genuinely carries that timestamp. An absent date and a 1970 date are
  // different facts and the card must not merge them.
  //
  // RED: this test PASSES on arrival — the shipped input guard is already correct, and there is no
  // red state to hand to green. Its worth was established by mutation instead: with
  // `|| date.getTime() === 0` appended to the validity guard, this test failed with
  // `Expected /^1 января 1970$/, Received: —` and the other six in this file stayed green. That
  // one-line mutation is the whole reason the fixture exists.
  it('renders a genuine 1970 timestamp as a real date, not as the placeholder', async () => {
    mockFeed([EPOCH_DATE_PROJECT], 1)

    renderProjectsPage()

    const card = await screen.findByTestId('project-card-document-21')

    expect(within(card).getByTestId('project-card-date')).toHaveTextContent(/^1 января 1970$/)
  })
})
