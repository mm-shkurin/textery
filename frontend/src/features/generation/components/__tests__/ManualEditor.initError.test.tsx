import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'
import { CREATE_FAILED_MESSAGE, LOAD_FAILED_MESSAGE } from '../../hooks/useDocumentInit'

vi.mock('../../api/documentApi')

// Init failing used to end at a `console.error`. That is the worst available outcome, because
// the page looks fine: with no documentId, ManualEditor's handleSave returns on its first line,
// so the Save button is inert and the status line sits on "Создание документа…" — a progress
// message for a request that gave up. The user types a whole document into a page that cannot
// keep it and is never told. These tests pin that the failure reaches the screen.
describe('ManualEditor initialisation failures', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows the API-authored message when creating the document fails', async () => {
    vi.mocked(documentApi.createDocument).mockRejectedValue(
      new Error('Не удалось создать документ (HTTP 500)'),
    )

    render(<ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={vi.fn()} />)

    // documentApi already built text a person can read — it is shown verbatim rather than
    // replaced by a generic string that discards the status it worked out.
    expect(await screen.findByTestId('me-init-error')).toHaveTextContent(
      'Не удалось создать документ (HTTP 500)',
    )
  })

  it('falls back to its own message when the failure carries no readable text', async () => {
    // A transport failure rejects with a bodyless error; `new Error('')` stands for "rejected
    // with nothing worth showing". The user still learns the editor cannot save.
    vi.mocked(documentApi.createDocument).mockRejectedValue(new Error(''))

    render(<ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={vi.fn()} />)

    expect(await screen.findByTestId('me-init-error')).toHaveTextContent(CREATE_FAILED_MESSAGE)
  })

  it('stops claiming the document is being created once creation has failed', async () => {
    vi.mocked(documentApi.createDocument).mockRejectedValue(new Error('boom'))

    render(<ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={vi.fn()} />)

    await screen.findByTestId('me-init-error')
    expect(screen.getByText('Документ не создан')).toBeInTheDocument()
    expect(screen.queryByText('Создание документа…')).not.toBeInTheDocument()
  })

  it('shows the failure when loading an existing document fails', async () => {
    vi.mocked(documentApi.getDocument).mockRejectedValue(new Error(''))

    render(
      <ManualEditor
        documentType="doklad"
        documentTypeLabel="Доклад"
        onBack={vi.fn()}
        existingDocumentId="doc-9"
      />,
    )

    expect(await screen.findByTestId('me-init-error')).toHaveTextContent(LOAD_FAILED_MESSAGE)
    expect(documentApi.createDocument).not.toHaveBeenCalled()
  })

  it('shows no error banner when initialisation succeeds', async () => {
    vi.mocked(documentApi.createDocument).mockResolvedValue({
      documentId: 'doc-1',
      status: 'draft',
      version: 7,
    })

    render(<ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('Черновик, ещё не сохранён')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('me-init-error')).not.toBeInTheDocument()
  })
})
