import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, within } from '@testing-library/react'
import { mockFeed, renderProjectsPage, resetFeedMocks } from './feedTestHarness'
import { DOCUMENT, GENERATION, OLDER_YEAR_PROJECT } from './projectFixtures'

vi.mock('../../api/projectsApi')

// Where the screen hands control back to its host. The page reaches the editor through flow state
// rather than a URL, so it cannot navigate itself — every exit is a callback, and a callback wired
// to the wrong row or fired with the wrong argument is a user opening someone else's document.
describe('ProjectsPage navigation', () => {
  resetFeedMocks()

  // The wire document type travels WITH the id: the host needs it to pick the editor's labels, and
  // re-fetching the row it already has just to read one field would be a second request for data
  // already on screen.
  it('opens a document by id and wire type', async () => {
    mockFeed([DOCUMENT], 1)
    const onOpenDocument = vi.fn()
    renderProjectsPage({ onOpenDocument })

    const card = await screen.findByTestId('project-card-document-1')
    fireEvent.click(within(card).getByRole('button', { name: DOCUMENT.title! }))

    expect(onOpenDocument).toHaveBeenCalledTimes(1)
    expect(onOpenDocument).toHaveBeenCalledWith(DOCUMENT.id, DOCUMENT.documentType)
  })

  // A generation's id comes from the other table entirely, so following it to the editor would
  // open nothing — or another user's row. The card renders; it simply offers no way through.
  it('offers no way to open a generation', async () => {
    mockFeed([GENERATION], 1)
    const onOpenDocument = vi.fn()
    renderProjectsPage({ onOpenDocument })

    const card = await screen.findByTestId('project-card-generation-1')
    expect(within(card).queryByRole('button', { name: GENERATION.title! })).toBeNull()
    expect(onOpenDocument).not.toHaveBeenCalled()
  })

  it('offers a way back when the host provides one', async () => {
    mockFeed([DOCUMENT], 1)
    const onBack = vi.fn()
    renderProjectsPage({ onBack })

    fireEvent.click(screen.getByTestId('projects-back'))
    expect(onBack).toHaveBeenCalledTimes(1)
  })

  // Rendered from a route with nowhere to go back to, the button would be a dead end. Absent
  // rather than disabled: there is no state in which it becomes available later.
  it('draws no back button when the host provides no target', async () => {
    mockFeed([DOCUMENT], 1)
    renderProjectsPage()

    await screen.findAllByTestId('project-card')
    expect(screen.queryByTestId('projects-back')).toBeNull()
  })

  // «Недавние проекты» is the first four items of the SAME response — never a second request for a
  // slice of data already in hand. It only earns its screenful once the page holds more than it
  // would show; repeating four cards the user can already see costs a section and buys nothing.
  it('shows no recent section when the feed fits inside it', async () => {
    mockFeed([DOCUMENT, GENERATION], 2)
    renderProjectsPage()

    await screen.findAllByTestId('project-card')
    expect(screen.queryByTestId('projects-recent')).toBeNull()
  })

  it('shortcuts the four newest projects once the feed is longer', async () => {
    const items = Array.from({ length: 6 }, (_, index) => ({
      ...OLDER_YEAR_PROJECT,
      id: String(index + 100),
      title: `Проект ${index}`,
    }))
    mockFeed(items, 6)
    renderProjectsPage()

    const recent = await screen.findByTestId('projects-recent')
    // Four, not six: the section is a shortcut, and the list below it still holds everything.
    expect(within(recent).getAllByTestId('recent-project-card')).toHaveLength(4)
    expect(screen.getAllByTestId('project-card')).toHaveLength(6)
    expect(within(recent).getByText('Недавние проекты')).toBeInTheDocument()
    expect(screen.getByText('Все проекты')).toBeInTheDocument()
  })

  // Under a search or a non-default order, "recent" stops describing what the section shows — it
  // would be "the first four of whatever you just sorted by", which is the list itself.
  it.each([
    ['a search is active', '/projects?q=проект'],
    ['the order is not the default', '/projects?sort=title_asc'],
  ])('hides the recent section when %s', async (_name, url) => {
    const items = Array.from({ length: 6 }, (_, index) => ({
      ...OLDER_YEAR_PROJECT,
      id: String(index + 100),
      title: `Проект ${index}`,
    }))
    mockFeed(items, 6)
    renderProjectsPage({}, url)

    await screen.findAllByTestId('project-card')
    expect(screen.queryByTestId('projects-recent')).toBeNull()
  })
})
