import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { mockFeed, mockFeedFailure, renderProjectsPage, resetFeedMocks } from './feedTestHarness'
import { DOCUMENT } from './projectFixtures'

vi.mock('../../api/projectsApi')

// Two empty states, never one. "Nothing matched" offers to clear the query; "no work yet" offers
// to create a project. Shipping one for both strands a new user on a search-reset button that does
// nothing — and strands a searching user on a «Создать проект» that throws away their query.
describe('ProjectsPage empty states', () => {
  resetFeedMocks()

  it('invites a user with no work to create a project', async () => {
    mockFeed([], 0)
    const onCreateProject = vi.fn()
    renderProjectsPage({ onCreateProject })

    const empty = await screen.findByTestId('projects-empty-none')
    expect(empty).toHaveTextContent('Работ пока нет.')
    expect(screen.queryByTestId('projects-empty-search')).toBeNull()

    fireEvent.click(screen.getByTestId('projects-create'))
    expect(onCreateProject).toHaveBeenCalledTimes(1)
  })

  it('offers to clear a search that matched nothing', async () => {
    mockFeed([], 0)
    renderProjectsPage({}, '/projects?q=ксчт')

    const empty = await screen.findByTestId('projects-empty-search')
    expect(empty).toHaveTextContent('Ничего не найдено.')
    expect(screen.queryByTestId('projects-empty-none')).toBeNull()
  })

  // A whitespace-only box is not a search. It has to take the "no work yet" arm, or a user who
  // fat-fingered a space is told their empty account matched nothing.
  it('treats a whitespace-only query as no search at all', async () => {
    mockFeed([], 0)
    renderProjectsPage({}, '/projects?q=%20%20')

    expect(await screen.findByTestId('projects-empty-none')).toBeInTheDocument()
  })

  // Clearing the search DELETES the parameter rather than setting it to '': the restored URL has
  // to be identical to the one a user who never searched would have.
  it('drops the query parameter when the search is cleared', async () => {
    mockFeed([], 0)
    renderProjectsPage({}, '/projects?q=ксчт')

    fireEvent.click(await screen.findByTestId('projects-clear-search'))

    await waitFor(() => expect(screen.getByTestId('projects-empty-none')).toBeInTheDocument())
    expect(screen.getByTestId('projects-search')).toHaveValue('')
  })

  // A failed load is NOT an empty feed. Resolving the failure to `items: []` would invite the user
  // to create their first project on top of a server fault — so while the banner is up, neither
  // empty state may appear.
  it('shows no empty state while a load failure is on screen', async () => {
    mockFeedFailure(new Error('Не удалось загрузить проекты'))
    renderProjectsPage()

    await screen.findByTestId('projects-error')
    expect(screen.queryByTestId('projects-empty-none')).toBeNull()
    expect(screen.queryByTestId('projects-empty-search')).toBeNull()
  })

  // The skeleton is decorative — it stands in for content that has not arrived, and announcing
  // four empty boxes to a screen reader is noise. `aria-hidden` is what keeps it out.
  it('hides the loading skeleton from assistive technology', () => {
    mockFeed([DOCUMENT], 1)
    renderProjectsPage()

    expect(screen.getByTestId('projects-loading')).toHaveAttribute('aria-hidden', 'true')
  })

  it('replaces the skeleton with the feed once it arrives', async () => {
    mockFeed([DOCUMENT], 1)
    renderProjectsPage()

    await screen.findAllByTestId('project-card')
    expect(screen.queryByTestId('projects-loading')).toBeNull()
  })
})
