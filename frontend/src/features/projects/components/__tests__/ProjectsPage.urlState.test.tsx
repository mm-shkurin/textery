import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { mockFeed, mockFeedFailure, renderProjectsPage, resetFeedMocks } from './feedTestHarness'
import { listProjects } from '../../api/projectsApi'
import { SEARCH_DEBOUNCE_MS } from '../../hooks/useProjectsFeed'
import { DOCUMENT } from './projectFixtures'

vi.mock('../../api/projectsApi')

/**
 * `q`, `sort` and `page` live in the query string rather than in component state — so opening a
 * project and coming back, refreshing, or sharing the link re-renders the same filtered feed
 * instead of an unfiltered page 1. That makes the URL a contract, and these are the ways it breaks:
 * a filter that never reaches the request, a page number kept across a filter change (the user
 * lands on an empty page 4 of a 3-page result and reads it as "nothing found"), and a debounce that
 * fires a request per keystroke.
 *
 * Driven through the page rather than by rendering the hook alone: the debounce and the request
 * are wired together by an effect, and a `renderHook` test would pin the hook's return value while
 * saying nothing about which request actually went out.
 */
describe('ProjectsPage url state', () => {
  resetFeedMocks()
  const mockedList = vi.mocked(listProjects)

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  // The filter the last request carried, without the cancellation signal the query cache attaches
  // to every fetch. These cases are about WHICH page was asked for; the signal is transport
  // plumbing that would otherwise have to be restated in each of the six assertions below.
  function lastQuery() {
    const params = mockedList.mock.calls[mockedList.mock.calls.length - 1][0]
    const { signal: _signal, ...filter } = params ?? {}
    return filter
  }

  it('asks for the filter the URL describes on first load', async () => {
    mockFeed([DOCUMENT], 1)
    renderProjectsPage({}, '/projects?q=эконом&sort=title_asc&page=3')

    await waitFor(() => expect(mockedList).toHaveBeenCalled())
    expect(lastQuery()).toEqual({ q: 'эконом', sort: 'title_asc', page: 3 })
  })

  // The defaults are the SERVER's, and the client states them only because the request shape needs
  // all three. `created_desc` and page 1 are what a bare `/projects` means.
  it('defaults to the newest-first first page', async () => {
    mockFeed([DOCUMENT], 1)
    renderProjectsPage()

    await waitFor(() => expect(mockedList).toHaveBeenCalled())
    expect(lastQuery()).toEqual({ q: '', sort: 'created_desc', page: 1 })
  })

  // A request per keystroke is what the debounce exists to prevent, and the only way to see it is
  // to type more than once inside one window.
  it('fires one request for a burst of typing', async () => {
    mockFeed([DOCUMENT], 1)
    renderProjectsPage()
    await waitFor(() => expect(mockedList).toHaveBeenCalledTimes(1))

    const box = screen.getByTestId('projects-search')
    fireEvent.change(box, { target: { value: 'э' } })
    fireEvent.change(box, { target: { value: 'эк' } })
    fireEvent.change(box, { target: { value: 'эко' } })

    // Still inside the window: nothing new may have gone out yet.
    vi.advanceTimersByTime(SEARCH_DEBOUNCE_MS - 1)
    expect(mockedList).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(2)
    await waitFor(() => expect(mockedList).toHaveBeenCalledTimes(2))
    expect(lastQuery()).toEqual({ q: 'эко', sort: 'created_desc', page: 1 })
  })

  // Changing the query returns to page 1. Keeping the number is the classic bug: the user lands on
  // an empty page 4 of a 3-page result and reads it as "nothing found".
  it('returns to the first page when the query changes', async () => {
    mockFeed([DOCUMENT], 100)
    renderProjectsPage({}, '/projects?page=4')
    await waitFor(() => expect(lastQuery()).toEqual({ q: '', sort: 'created_desc', page: 4 }))

    fireEvent.change(screen.getByTestId('projects-search'), { target: { value: 'э' } })
    vi.advanceTimersByTime(SEARCH_DEBOUNCE_MS + 1)

    await waitFor(() => expect(lastQuery()).toEqual({ q: 'э', sort: 'created_desc', page: 1 }))
  })

  it('returns to the first page when the order changes', async () => {
    mockFeed([DOCUMENT], 100)
    renderProjectsPage({}, '/projects?page=4')
    await waitFor(() => expect(lastQuery()).toEqual({ q: '', sort: 'created_desc', page: 4 }))

    fireEvent.change(screen.getByTestId('projects-sort'), { target: { value: 'type_asc' } })

    await waitFor(() => expect(lastQuery()).toEqual({ q: '', sort: 'type_asc', page: 1 }))
  })

  // Paging keeps the filter. A pager that dropped `q` would walk the user out of their own search
  // on the second page.
  it('keeps the query and the order when paging', async () => {
    mockFeed([DOCUMENT], 100)
    renderProjectsPage({}, '/projects?q=эко&sort=title_asc')
    await waitFor(() => expect(mockedList).toHaveBeenCalled())

    fireEvent.click(await screen.findByTestId('projects-page-next'))

    await waitFor(() => expect(lastQuery()).toEqual({ q: 'эко', sort: 'title_asc', page: 2 }))
  })

  // Retrying re-issues the request with the SAME q and sort — a retry that reset them would answer
  // a different question than the one that failed.
  it('retries the request that failed, filter intact', async () => {
    mockFeedFailure(new Error('Не удалось загрузить проекты'))
    renderProjectsPage({}, '/projects?q=эко&sort=title_asc&page=2')

    fireEvent.click(await screen.findByTestId('projects-error-retry'))

    await waitFor(() => expect(mockedList).toHaveBeenCalledTimes(2))
    expect(lastQuery()).toEqual({ q: 'эко', sort: 'title_asc', page: 2 })
  })
})
