import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'

vi.mock('../../api/documentApi')

describe('ManualEditor', () => {
  it('creates the document on mount and flips save status once creation resolves', async () => {
    // The API's own type, not a hand-written shape: this deferred previously spelled out
    // `{ documentId, status }` and so kept compiling after `version` became part of the
    // contract, which is how a mock drifts from the thing it stands for.
    let resolveCreate: (value: documentApi.CreateDocumentResult) => void = () => {}
    const createPromise = new Promise<documentApi.CreateDocumentResult>((resolve) => {
      resolveCreate = resolve
    })
    vi.mocked(documentApi.createDocument).mockReturnValue(createPromise)

    render(<ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={vi.fn()} />)

    expect(documentApi.createDocument).toHaveBeenCalledWith('doklad', expect.any(String))
    expect(screen.getByText('Создание документа…')).toBeInTheDocument()

    resolveCreate({ documentId: 'doc-1', status: 'draft', version: 7 })

    await waitFor(() => {
      expect(screen.getByText('Черновик, ещё не сохранён')).toBeInTheDocument()
    })
  })
})
