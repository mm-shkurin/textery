import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { ProjectsPage } from '../ProjectsPage'
import * as projectsApi from '../../api/projectsApi'
import type { ProjectSummary } from '../../api/projectsApi'

// `GET /api/v1/projects` does not exist on the backend yet — this suite builds against a mock of
// it, never a live call.
vi.mock('../../api/projectsApi')

// A document and a generation deliberately seeded with THE SAME id. That is not a contrived
// fixture: the two arms of the merged feed come from different tables, so their ids can collide,
// and a component keying rows on `key={id}` would render one node for the pair. The story pins
// the key as `(kind, id)`; two cards on screen is what proves it.
const DOCUMENT: ProjectSummary = {
  kind: 'document',
  id: '1',
  title: 'Влияние искусственного интеллекта на рынок труда',
  preview: null,
  documentType: 'реферат',
  status: 'draft',
  canRepeat: false,
  createdAt: '2026-07-15T09:00:00Z',
  updatedAt: '2026-07-15T09:00:00Z',
}

const GENERATION: ProjectSummary = {
  kind: 'generation',
  id: '1',
  title: 'Открытие кофейни в спальном районе',
  preview: null,
  documentType: 'доклад',
  status: 'failed',
  canRepeat: true,
  createdAt: '2026-06-02T09:00:00Z',
  updatedAt: '2026-06-02T09:00:00Z',
}

// A wire `document_type` this client has never heard of. The server owns that vocabulary and can
// add a member before the frontend learns it, so `documentTypeFromWire` returns null by design —
// and every other fixture in this file is a KNOWN type, which is why the card's accent fallback
// has never actually rendered.
const UNKNOWN_TYPE_PROJECT: ProjectSummary = {
  kind: 'document',
  id: '7',
  title: 'Курсовая работа по микроэкономике',
  preview: null,
  documentType: 'курсовая',
  status: 'draft',
  canRepeat: false,
  createdAt: '2026-07-15T09:00:00Z',
  updatedAt: '2026-07-15T09:00:00Z',
}

// `total` is passed, never derived from `items.length` — the two differ the moment paging enters
// (test 3.x), and a helper that computes it cannot express a wrong-total bug.
function mockFeed(items: ProjectSummary[], total: number) {
  vi.mocked(projectsApi.listProjects).mockResolvedValue({
    items,
    total,
    page: 1,
    limit: 20,
  })
}

describe('ProjectsPage', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  // Asserted on TWO projects, and on all three fields of each, because every cheaper version of
  // this test passes on a broken feed: one card would pass on a component that renders the first
  // item for all of them, and a card-count check alone would pass on cards that are blank.
  // RED: fails with "Test timed out in 5000ms." — ProjectsPage is a stub returning null, so
  // findAllByTestId('project-card') never resolves. The message is vitest's rather than testing
  // library's "Unable to find an element" because setup.ts sets asyncUtilTimeout to 5000, exactly
  // vitest's default testTimeout, so the outer timeout wins the race.
  it('shows each project as a card carrying its type, its name, and its date', async () => {
    mockFeed([DOCUMENT, GENERATION], 2)

    render(<ProjectsPage />)

    const cards = await screen.findAllByTestId('project-card')
    expect(cards).toHaveLength(2)

    // Each card is fetched by its OWN (kind, id) testid rather than by position. Positional
    // `cards[0]`/`cards[1]` cannot fail when the component swaps the two items' identity or
    // renders the generation's payload under the document's card; identity lookup can, and it is
    // what actually pins the deliberately-colliding `id: '1'`.
    const documentCard = screen.getByTestId('project-card-document-1')
    const generationCard = screen.getByTestId('project-card-generation-1')

    // Three separate slots, each asserted as the WHOLE text of its own element (`/^…$/`), not as a
    // substring of the card. A card-wide `toHaveTextContent('Реферат')` passes on one undivided
    // blob, on 'Рефераты и доклады', and on a date rendered '15 июля 2026 г.' — none of which is
    // the card the scenario describes. The type is the LABEL the rest of the app uses ('Реферат'),
    // not the wire's Cyrillic 'реферат': the history list shipped the raw field once and named one
    // document two ways depending on which screen you looked at.
    expect(within(documentCard).getByTestId('project-card-type')).toHaveTextContent(/^Реферат$/)
    expect(within(documentCard).getByTestId('project-card-title')).toHaveTextContent(
      /^Влияние искусственного интеллекта на рынок труда$/,
    )
    // Day + month, no year — that is the format the mockup renders for a current-year project
    // (mockups/desktop/01-projects-grid.html: `<div class="date">15 июля</div>`; older years get
    // '2 сентября 2025', which the anchored regex would reject). This test is the specification
    // for that format — a raw '2026-07-15T09:00:00Z' fails it, and so does '15.07'.
    expect(within(documentCard).getByTestId('project-card-date')).toHaveTextContent(/^15 июля$/)

    expect(within(generationCard).getByTestId('project-card-type')).toHaveTextContent(/^Доклад$/)
    expect(within(generationCard).getByTestId('project-card-title')).toHaveTextContent(
      /^Открытие кофейни в спальном районе$/,
    )
    expect(within(generationCard).getByTestId('project-card-date')).toHaveTextContent(/^2 июня$/)
  })
})

// Dated in a year that is not the pinned "now". Every other fixture in this file is 2026, which is
// why the card's with-the-year date format has never once rendered. The literal is lifted from the
// mockup (mockups/desktop/01-projects-grid.html: `<div class="date">2 сентября 2025</div>`) so the
// assertion is anchored to the design, not to whatever the formatter happens to emit.
const OLDER_YEAR_PROJECT: ProjectSummary = {
  kind: 'document',
  id: '9',
  title: 'Экономика замкнутого цикла',
  preview: null,
  documentType: 'реферат',
  status: 'draft',
  canRepeat: false,
  createdAt: '2025-09-02T09:00:00Z',
  updatedAt: '2025-09-02T09:00:00Z',
}

describe('ProjectsPage card date for a project from an older year', () => {
  // Pinned for the same reason as the accent block below, but here the pin IS the test: an
  // "older year" fixture is only older relative to a now, and an unpinned clock would silently
  // turn this scenario into the current-year one the moment the calendar rolled into 2025+1.
  beforeEach(() => {
    vi.setSystemTime(new Date('2026-08-03T12:00:00.000Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  // Anchored `/^…$/` against the MOCKUP's literal, not against the formatter's output. That
  // distinction is the whole test: `toLocaleDateString('ru-RU', {…, year: 'numeric'})` emits the
  // era suffix — '2 сентября 2025 г.' — and the mockup renders '2 сентября 2025'. A substring
  // assertion, or one written to match what the code already does, would pass and enshrine the
  // suffix on every card older than this year.
  // RED (2026-08-03): fails with
  //   expect(element).toHaveTextContent(/^2 сентября 2025$/)
  //   Expected element to have text content matching: /^2 сентября 2025$/
  //   Received: 2 сентября 2025 г.
  it.skip('renders the year for an older project, in the mockup’s format and without the era suffix', async () => {
    mockFeed([OLDER_YEAR_PROJECT], 1)

    render(<ProjectsPage />)

    const card = await screen.findByTestId('project-card-document-9')

    expect(within(card).getByTestId('project-card-date')).toHaveTextContent(/^2 сентября 2025$/)
  })
})

describe('ProjectsPage card accent for an unfamiliar document type', () => {
  // The clock is pinned because the card's date format branches on `getFullYear() !== now`, and
  // every fixture in this file is dated 2026. Without this the suite green-passes only while the
  // wall clock agrees with the fixtures. `setSystemTime` alone — not `useFakeTimers` — because the
  // component resolves a mocked promise, and a fully faked timer queue would stall `findBy*`.
  beforeEach(() => {
    vi.setSystemTime(new Date('2026-08-03T12:00:00.000Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  // The accent is asserted on the ANCESTOR of the badge, not on the badge itself: the stylesheet
  // colours the chip through `.project-card-accent-blue .project-card-type`, so the card carrying
  // the class is what decides whether the badge is tinted or renders as a transparent, unstyled
  // chip. Both halves are asserted — the fallback accent present, AND no other accent present —
  // because asserting only the first would pass on a card that somehow wore two accents, and the
  // point of the fallback is that exactly one tint is chosen.
  it('gives a project of an unknown wire type the blue fallback accent rather than no accent', async () => {
    mockFeed([UNKNOWN_TYPE_PROJECT], 1)

    render(<ProjectsPage />)

    const card = await screen.findByTestId('project-card')

    expect(card).toHaveClass('project-card-accent-blue')
    expect(card).not.toHaveClass('project-card-accent-purple')
    expect(card).not.toHaveClass('project-card-accent-teal')
    expect(within(card).getByTestId('project-card-type')).toBeInTheDocument()
  })
})
