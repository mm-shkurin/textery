import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { HistoryPage } from '../HistoryPage'
import * as historyApi from '../../api/historyApi'

vi.mock('../../api/historyApi')

// `role="tab"` is a promise about keyboard behaviour, not a styling hook. The tablist declared it
// and delivered none of it: no ids, no aria-controls, no tabpanel, and both tabs in the tab
// order. Half a pattern is worse than none — it tells a screen-reader user "tab 1 of 2" and then
// behaves like two ordinary buttons next to unrelated content. These pin the other half.
describe('HistoryPage tabs — the ARIA pattern the tablist promises', () => {
  beforeEach(() => {
    vi.mocked(historyApi.listDocuments).mockResolvedValue({ items: [], nextCursor: null })
    vi.mocked(historyApi.listGenerations).mockResolvedValue({ items: [], nextCursor: null })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  function renderPage() {
    render(<HistoryPage onOpenDocument={vi.fn()} onBack={vi.fn()} />)
  }

  it('points each tab at the panel it controls, and labels the panel by its tab', () => {
    renderPage()

    const documentsTab = screen.getByTestId('history-tab-documents')
    const panel = screen.getByRole('tabpanel')

    expect(documentsTab).toHaveAttribute('aria-controls', panel.id)
    expect(panel).toHaveAttribute('aria-labelledby', documentsTab.id)
  })

  it('keeps the whole tablist to a single tab stop', () => {
    renderPage()

    // Roving tabindex: only the selected tab is reachable with Tab, the arrows do the rest.
    // Without it, every tab added to this list adds another stop to get past.
    expect(screen.getByTestId('history-tab-documents')).toHaveAttribute('tabindex', '0')
    expect(screen.getByTestId('history-tab-generations')).toHaveAttribute('tabindex', '-1')
  })

  it('moves between tabs with the arrow keys, and wraps at the ends', () => {
    renderPage()

    fireEvent.keyDown(screen.getByTestId('history-tab-documents'), { key: 'ArrowRight' })
    expect(screen.getByTestId('history-tab-generations')).toHaveAttribute('aria-selected', 'true')

    // Wrapping, per the APG pattern: the ends of a tablist are not walls.
    fireEvent.keyDown(screen.getByTestId('history-tab-generations'), { key: 'ArrowRight' })
    expect(screen.getByTestId('history-tab-documents')).toHaveAttribute('aria-selected', 'true')

    fireEvent.keyDown(screen.getByTestId('history-tab-documents'), { key: 'ArrowLeft' })
    expect(screen.getByTestId('history-tab-generations')).toHaveAttribute('aria-selected', 'true')
  })

  it('leaves other keys to the browser', () => {
    renderPage()

    fireEvent.keyDown(screen.getByTestId('history-tab-documents'), { key: 'ArrowDown' })

    // A horizontal tablist must not eat vertical arrows — that is the page's scroll.
    expect(screen.getByTestId('history-tab-documents')).toHaveAttribute('aria-selected', 'true')
  })

  it('re-labels the panel when the selected tab changes', () => {
    renderPage()

    fireEvent.click(screen.getByTestId('history-tab-generations'))

    const panel = screen.getByRole('tabpanel')
    expect(panel).toHaveAttribute('aria-labelledby', screen.getByTestId('history-tab-generations').id)
  })
})
