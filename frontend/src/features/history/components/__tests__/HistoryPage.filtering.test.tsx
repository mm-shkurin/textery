import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { HistoryPage } from '../HistoryPage'
import * as historyApi from '../../api/historyApi'

vi.mock('../../api/historyApi')

const DOC = {
  documentId: 'doc-1',
  documentType: 'доклад',
  status: 'draft',
  title: 'Квантовые компьютеры',
  version: 2,
  createdAt: '2026-07-17T10:00:00Z',
  updatedAt: '2026-07-17T11:00:00Z',
}

function renderPage() {
  render(<HistoryPage onOpenDocument={vi.fn()} onBack={vi.fn()} />)
}

// The last filter object the page asked the API for. Read off the LAST call rather than the first:
// the screen refetches when the filter changes, and the assertion is about where it ended up.
function lastFilter() {
  const calls = vi.mocked(historyApi.listDocuments).mock.calls
  return calls[calls.length - 1][2]
}

describe('HistoryPage — «поиск по истории» and «фильтровать по дате создания»', () => {
  beforeEach(() => {
    vi.mocked(historyApi.listDocuments).mockResolvedValue({ items: [DOC], nextCursor: null })
    vi.mocked(historyApi.listGenerations).mockResolvedValue({ items: [], nextCursor: null })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('asks the server for the search text rather than filtering the loaded page', async () => {
    renderPage()
    await screen.findByTestId('history-document-row')

    fireEvent.change(screen.getByTestId('history-search'), { target: { value: 'квантовые' } })

    // The narrowing has to reach the SERVER: filtering the loaded page would search twenty rows
    // out of a history with ten pages of them, and report "ничего не найдено" for a document the
    // user is sure they wrote.
    await waitFor(() => expect(lastFilter()).toMatchObject({ query: 'квантовые' }))
  })

  it('sends both ends of the date window', async () => {
    renderPage()
    await screen.findByTestId('history-document-row')

    fireEvent.change(screen.getByTestId('history-created-from'), {
      target: { value: '2026-07-01' },
    })
    fireEvent.change(screen.getByTestId('history-created-to'), { target: { value: '2026-07-31' } })

    await waitFor(() =>
      expect(lastFilter()).toMatchObject({ createdFrom: '2026-07-01', createdTo: '2026-07-31' }),
    )
  })

  it('keeps the dates when the search text changes', async () => {
    renderPage()
    await screen.findByTestId('history-document-row')

    fireEvent.change(screen.getByTestId('history-created-from'), {
      target: { value: '2026-07-01' },
    })
    fireEvent.change(screen.getByTestId('history-search'), { target: { value: 'отчёт' } })

    // The three controls write into ONE filter. Split across three pieces of state, typing in the
    // search box would fire a request that had forgotten the date the user already picked.
    await waitFor(() =>
      expect(lastFilter()).toMatchObject({ query: 'отчёт', createdFrom: '2026-07-01' }),
    )
  })

  it('clears every control at once when the filter is reset', async () => {
    renderPage()
    await screen.findByTestId('history-document-row')

    fireEvent.change(screen.getByTestId('history-search'), { target: { value: 'отчёт' } })
    fireEvent.change(screen.getByTestId('history-created-from'), {
      target: { value: '2026-07-01' },
    })
    await screen.findByTestId('history-filter-reset')

    fireEvent.click(screen.getByTestId('history-filter-reset'))

    // Asserted on the CONTROLS, not on a fresh request: returning to the unfiltered list is a
    // cache hit — the pages were already loaded under that key — so demanding a new fetch here
    // would be pinning a refetch the screen is right not to make.
    //
    // One reset for all three: clearing the search box by hand leaves the date in place, and a
    // user looking at an empty list with an empty search box cannot tell that it is still narrowed.
    await waitFor(() => expect(screen.queryByTestId('history-filter-reset')).toBeNull())
    expect(screen.getByTestId('history-search')).toHaveValue('')
    expect(screen.getByTestId('history-created-from')).toHaveValue('')
  })

  it('does not reload the page when the search form is submitted', async () => {
    renderPage()
    await screen.findByTestId('history-document-row')
    const form = screen.getByTestId('history-search').closest('form')!

    const submit = new Event('submit', { bubbles: true, cancelable: true })
    form.dispatchEvent(submit)

    // Enter in a search box submits the form, and a real submit would reload the page and throw
    // away every loaded row.
    expect(submit.defaultPrevented).toBe(true)
  })

  it('offers no reset while nothing is narrowed', async () => {
    renderPage()
    await screen.findByTestId('history-document-row')

    expect(screen.queryByTestId('history-filter-reset')).toBeNull()
  })

  it('says the list is empty because of the search, not because nothing was ever created', async () => {
    renderPage()
    await screen.findByTestId('history-document-row')
    vi.mocked(historyApi.listDocuments).mockResolvedValue({ items: [], nextCursor: null })

    fireEvent.change(screen.getByTestId('history-search'), { target: { value: 'ничего' } })

    // «Вы ещё не создавали работ» under an active search tells a user with fifty documents that
    // they have none.
    expect(await screen.findByText('Ничего не найдено по этому запросу.')).toBeInTheDocument()
  })
})
