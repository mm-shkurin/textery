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

// A SECOND older-year fixture, and the reason it is not redundant with the one above: one
// assertion pins one month and one year, so the cheapest way to satisfy it is a hand-rolled
// Russian genitive month table — eleven of whose entries no test would ever read. This fixture
// picks a different month AND a different year, both lifted from the same mockup
// (mockups/desktop/01-projects-grid.html: `<div class="date">16 декабря 2024</div>`), so the
// table has to be right twice before it is cheaper than keeping `toLocaleDateString`.
const SECOND_OLDER_YEAR_PROJECT: ProjectSummary = {
  kind: 'document',
  id: '11',
  title: 'История отечественной архитектуры',
  preview: null,
  documentType: 'реферат',
  status: 'draft',
  canRepeat: false,
  createdAt: '2024-12-16T12:00:00Z',
  updatedAt: '2024-12-16T12:00:00Z',
}

// The only fixture in this file whose `createdAt` and `updatedAt` are NOT the same string. Every
// other one aliases them, which means the card could be reading `createdAt` and the whole suite
// would stay green. `12_MyProjects.md` makes the two equal only at birth ("its `updated_at` equal
// to its `created_at`") and names `updated_at` a sort key — they diverge on the first save, and
// the feed's job is telling recently-touched work apart. The two dates are chosen to format
// differently: the creation renders with a year ('5 марта 2024'), the edit without one
// ('15 июля'), so a card reading the wrong field cannot accidentally satisfy the assertion.
const EDITED_LONG_AFTER_CREATION_PROJECT: ProjectSummary = {
  kind: 'document',
  id: '13',
  title: 'Цифровизация городского транспорта',
  preview: null,
  documentType: 'реферат',
  status: 'draft',
  canRepeat: false,
  createdAt: '2024-03-05T12:00:00Z',
  updatedAt: '2026-07-15T12:00:00Z',
}

// Two fixtures for two ways the same field goes bad, because ONE `isNaN` guard fixes only the
// first. `projectsApi.ts` maps `item.updated_at` straight through with no validation, against an
// endpoint the backend has not built (`endpoints.md`) — so what arrives is whatever the server
// eventually sends, and `ProjectSummary.updatedAt: string` is a compile-time claim about a runtime
// JSON body, which is why both casts below are `as unknown as string` rather than fixture sloppiness.
//
// Malformed: `new Date('30 февраля, наверное')` is an Invalid Date, `getFullYear()` is NaN, and
// `NaN !== currentYear` is TRUE — so the card takes the year-SHOWING branch and concatenates two
// failure tokens into 'Invalid Date NaN'. Verified in this repo's node.
const UNPARSEABLE_DATE_PROJECT: ProjectSummary = {
  kind: 'document',
  id: '15',
  title: 'Проект с испорченной датой',
  preview: null,
  documentType: 'реферат',
  status: 'draft',
  canRepeat: false,
  createdAt: '2026-07-15T09:00:00Z',
  updatedAt: '30 февраля, наверное' as unknown as string,
}

// Missing: `new Date(null)` is the epoch — a perfectly VALID Date — so it renders '1 января 1970',
// which reads to the user as a real edit date rather than as an absent one. That is the worse half
// of the pair and the reason it is pinned here: a green fix that only checks `isNaN(getTime())`
// leaves this card lying. Verified in this repo's node.
const MISSING_DATE_PROJECT: ProjectSummary = {
  kind: 'document',
  id: '17',
  title: 'Проект без даты',
  preview: null,
  documentType: 'реферат',
  status: 'draft',
  canRepeat: false,
  createdAt: '2026-07-15T09:00:00Z',
  updatedAt: null as unknown as string,
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

// Called from inside a `describe`, never at file scope — the first block below is deliberately
// left on the real clock, and a top-level pin would silently cover it. The instant stays at the
// call site rather than baked in here, because "older year" and "renders without a year" are both
// claims about a fixture's date RELATIVE to this now; a reader of the block has to see it.
// `setSystemTime` alone — not `useFakeTimers` — because the component resolves a mocked promise,
// and a fully faked timer queue would stall `findBy*`.
function pinClockTo(instant: string) {
  beforeEach(() => {
    vi.setSystemTime(new Date(instant))
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
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
  // with a real date on every card and has no absent-date state — so inventing a Russian
  // placeholder ('Дата неизвестна', '—') would put a string on screen that appears in neither the
  // story nor the design. The defensible reading of that silence is that the card shows no date
  // TEXT, and the element itself stays (empty) rather than being omitted: the date slot is a grid
  // row in `projects.css`, and dropping the node reflows the card's other two lines.
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

describe('ProjectsPage card accent for an unfamiliar document type', () => {
  // The clock is pinned because the card's date format branches on `getFullYear() !== now`, and
  // this block's fixture is dated 2026. Without this the suite green-passes only while the wall
  // clock agrees with the fixture.
  pinClockTo('2026-08-03T12:00:00.000Z')

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
