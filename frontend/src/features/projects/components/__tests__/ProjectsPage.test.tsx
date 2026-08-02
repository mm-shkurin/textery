import { afterEach, describe, expect, it, vi } from 'vitest'
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
