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

async function openTheConfirmation() {
  renderPage()
  await screen.findByTestId('history-document-row')
  fireEvent.click(screen.getByTestId('history-document-delete'))
  return await screen.findByTestId('history-delete-confirm')
}

describe('HistoryPage — «удалить текст из истории»', () => {
  beforeEach(() => {
    vi.mocked(historyApi.listDocuments).mockResolvedValue({ items: [DOC], nextCursor: null })
    vi.mocked(historyApi.listGenerations).mockResolvedValue({ items: [], nextCursor: null })
    vi.mocked(historyApi.deleteDocument).mockResolvedValue(undefined)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('deletes nothing on the first press', async () => {
    await openTheConfirmation()

    // The control is a small ✕ one row away from twenty others and the action cannot be undone.
    // A press that deleted outright would make a mis-click unrecoverable.
    expect(historyApi.deleteDocument).not.toHaveBeenCalled()
  })

  it('names the work being deleted in the confirmation', async () => {
    const dialog = await openTheConfirmation()

    // Without the title the dialog cannot tell the user WHICH of twenty rows they hit.
    expect(dialog).toHaveTextContent('Квантовые компьютеры')
  })

  it('names an untitled work by its type rather than showing an empty gap', async () => {
    vi.mocked(historyApi.listDocuments).mockResolvedValue({
      items: [{ ...DOC, title: null }],
      nextCursor: null,
    })

    // A manual document created before titles existed has none. «Удалить «»?» tells the user
    // nothing about what they are about to lose.
    expect(await openTheConfirmation()).toHaveTextContent('Доклад')
  })

  it('deletes the document the user confirmed', async () => {
    await openTheConfirmation()

    fireEvent.click(screen.getByTestId('history-delete-submit'))

    await waitFor(() => expect(historyApi.deleteDocument).toHaveBeenCalledWith('doc-1'))
  })

  it('deletes nothing when the confirmation is dismissed', async () => {
    await openTheConfirmation()

    fireEvent.click(screen.getByTestId('history-delete-cancel'))

    await waitFor(() => expect(screen.queryByTestId('history-delete-confirm')).toBeNull())
    expect(historyApi.deleteDocument).not.toHaveBeenCalled()
  })

  it('reloads the list once the row is gone', async () => {
    await openTheConfirmation()
    const before = vi.mocked(historyApi.listDocuments).mock.calls.length

    fireEvent.click(screen.getByTestId('history-delete-submit'))

    // Refetched rather than spliced out of the cached page: the list is paged by keyset cursor, so
    // removing a row locally leaves the following pages anchored to cursors computed before the
    // delete — and «показать ещё» then skips a row for every one removed.
    await waitFor(() =>
      expect(vi.mocked(historyApi.listDocuments).mock.calls.length).toBeGreaterThan(before),
    )
  })

  it('dismisses the confirmation on Escape', async () => {
    await openTheConfirmation()

    fireEvent.keyDown(document, { key: 'Escape' })

    // Escape is the way out of every dialog on the platform, and this one must not be the
    // exception that traps somebody in front of an irreversible button.
    await waitFor(() => expect(screen.queryByTestId('history-delete-confirm')).toBeNull())
    expect(historyApi.deleteDocument).not.toHaveBeenCalled()
  })

  it('ignores Escape while the delete is in flight', async () => {
    let settle = () => {}
    vi.mocked(historyApi.deleteDocument).mockReturnValue(
      new Promise<void>((resolve) => {
        settle = resolve
      }),
    )
    await openTheConfirmation()
    fireEvent.click(screen.getByTestId('history-delete-submit'))
    await waitFor(() => expect(historyApi.deleteDocument).toHaveBeenCalled())

    fireEvent.keyDown(document, { key: 'Escape' })

    // The DELETE is already gone; closing here would hide its answer, so the dialog stays until
    // the request settles.
    expect(screen.getByTestId('history-delete-confirm')).toBeInTheDocument()
    settle()
  })

  it('sends one DELETE however many times the confirm is pressed', async () => {
    let settle = () => {}
    vi.mocked(historyApi.deleteDocument).mockReturnValue(
      new Promise<void>((resolve) => {
        settle = resolve
      }),
    )
    await openTheConfirmation()

    fireEvent.click(screen.getByTestId('history-delete-submit'))
    fireEvent.click(screen.getByTestId('history-delete-submit'))

    // The second press would answer 404 — the first delete having succeeded — and surface as a
    // failure for an operation that actually worked.
    await waitFor(() => expect(historyApi.deleteDocument).toHaveBeenCalledTimes(1))
    settle()
  })

  it('keeps the confirmation open and explains itself when the delete fails', async () => {
    vi.mocked(historyApi.deleteDocument).mockRejectedValue(new Error('Сервер недоступен'))
    await openTheConfirmation()

    fireEvent.click(screen.getByTestId('history-delete-submit'))

    // Closing on failure would leave the row on screen with no explanation, which reads as
    // "the delete silently did nothing".
    expect(await screen.findByTestId('history-delete-error')).toHaveTextContent('Сервер недоступен')
    expect(screen.getByTestId('history-delete-confirm')).toBeInTheDocument()
  })
})
