import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { HistoryPage } from '../HistoryPage'
import * as historyApi from '../../api/historyApi'

vi.mock('../../api/historyApi')

const DOC = {
  documentId: 'doc-1',
  documentType: 'доклад',
  status: 'draft',
  version: 2,
  createdAt: '2026-07-17T10:00:00Z',
  updatedAt: '2026-07-17T11:00:00Z',
}

function renderPage(onOpenDocument = vi.fn()) {
  render(<HistoryPage onOpenDocument={onOpenDocument} onBack={vi.fn()} />)
  return { onOpenDocument }
}

describe('HistoryPage', () => {
  beforeEach(() => {
    vi.mocked(historyApi.listGenerations).mockResolvedValue({ items: [], nextCursor: null })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  // The row shows the LABEL, not the wire value. `document_type` arrives as the backend's
  // Cyrillic 'доклад'; every other surface (the type modal that created it, the editor's
  // breadcrumb) says 'Доклад'. The list used to render the raw field, so one document was named
  // two ways depending on where you looked at it.
  it('labels a document row the way the rest of the app names that type', async () => {
    vi.mocked(historyApi.listDocuments).mockResolvedValue({ items: [DOC], nextCursor: null })

    renderPage()

    expect(await screen.findByTestId('history-document-row')).toHaveTextContent('Доклад')
  })

  // The server owns this value and can add a type before the client knows it. The row falls back
  // to the wire string rather than a placeholder — for an unknown type that string is the most
  // informative thing available, and it must not crash the whole list either.
  it('falls back to the wire value for a document type it does not know', async () => {
    vi.mocked(historyApi.listDocuments).mockResolvedValue({
      items: [{ ...DOC, documentType: 'диссертация' }],
      nextCursor: null,
    })

    renderPage()

    expect(await screen.findByTestId('history-document-row')).toHaveTextContent('диссертация')
  })

  it('opens a document by id AND wire type — the type is what labels the editor', async () => {
    vi.mocked(historyApi.listDocuments).mockResolvedValue({ items: [DOC], nextCursor: null })
    const { onOpenDocument } = renderPage()

    fireEvent.click(await screen.findByTestId('history-document-row'))

    // Both arguments asserted: passing only the id compiles and renders identically, and the
    // editor's breadcrumb would silently fall back to 'Доклад' for every document type.
    expect(onOpenDocument).toHaveBeenCalledExactlyOnceWith('doc-1', 'доклад')
  })

  it('says the list is empty rather than showing nothing at all', async () => {
    vi.mocked(historyApi.listDocuments).mockResolvedValue({ items: [], nextCursor: null })

    renderPage()

    expect(await screen.findByTestId('history-documents-empty')).toBeInTheDocument()
  })

  // The distinction that matters: a failed fetch also leaves items empty. Telling someone "you
  // have no documents" when the truth is "we could not ask" invites them to recreate work that
  // already exists.
  it('shows an error, not an empty state, when the list fails to load', async () => {
    vi.mocked(historyApi.listDocuments).mockRejectedValue(new Error('Не удалось загрузить документы'))

    renderPage()

    const error = await screen.findByTestId('history-documents-error')
    expect(error).toHaveTextContent('Не удалось загрузить документы')
    expect(screen.queryByTestId('history-documents-empty')).not.toBeInTheDocument()
  })

  it('pages with the cursor and appends, rather than replacing what is on screen', async () => {
    const second = { ...DOC, documentId: 'doc-2' }
    vi.mocked(historyApi.listDocuments)
      .mockResolvedValueOnce({ items: [DOC], nextCursor: 'cur-1' })
      .mockResolvedValueOnce({ items: [second], nextCursor: null })

    renderPage()

    fireEvent.click(await screen.findByTestId('history-documents-more'))

    await waitFor(() => expect(screen.getAllByTestId('history-document-row')).toHaveLength(2))
    // The page size is left to the client's own default (which is the server's): this component
    // has no opinion about it, and stating 20 here made a third copy of one number.
    expect(historyApi.listDocuments).toHaveBeenNthCalledWith(2, undefined, 'cur-1')
    // The cursor is null now, so the control must be gone — not merely disabled. Asserting the
    // row count alone would pass on a list that keeps offering a page that does not exist.
    expect(screen.queryByTestId('history-documents-more')).not.toBeInTheDocument()
  })

  // hasMore is derived from the cursor, never from items.length === limit. A full last page
  // (items exactly filling the limit, cursor null) must not offer another page.
  it('offers no next page when the cursor is null, however many rows came back', async () => {
    vi.mocked(historyApi.listDocuments).mockResolvedValue({
      items: [DOC, { ...DOC, documentId: 'doc-2' }],
      nextCursor: null,
    })

    renderPage()

    await screen.findAllByTestId('history-document-row')
    expect(screen.queryByTestId('history-documents-more')).not.toBeInTheDocument()
  })

  it('switching tabs asks the other endpoint, not the same one again', async () => {
    vi.mocked(historyApi.listDocuments).mockResolvedValue({ items: [DOC], nextCursor: null })
    vi.mocked(historyApi.listGenerations).mockResolvedValue({
      items: [
        {
          generationId: 'gen-1',
          status: 'completed',
          topic: 'Квантовые компьютеры',
          documentType: 'доклад',
          volumePages: 5,
          createdAt: '2026-07-17T09:00:00Z',
        },
      ],
      nextCursor: null,
    })

    renderPage()
    await screen.findByTestId('history-document-row')

    fireEvent.click(screen.getByTestId('history-tab-generations'))

    expect(await screen.findByTestId('history-generation-row')).toHaveTextContent(
      'Квантовые компьютеры',
    )
    expect(screen.queryByTestId('history-document-row')).not.toBeInTheDocument()
  })
})
