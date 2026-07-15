import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'

vi.mock('../../api/documentApi')

describe('ManualEditor', () => {
  it('creates the document on mount and flips save status once creation resolves', async () => {
    let resolveCreate: (value: { documentId: string; status: string }) => void = () => {}
    const createPromise = new Promise<{ documentId: string; status: string }>((resolve) => {
      resolveCreate = resolve
    })
    vi.mocked(documentApi.createDocument).mockReturnValue(createPromise)

    render(<ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={vi.fn()} />)

    expect(documentApi.createDocument).toHaveBeenCalledWith('doklad')
    expect(screen.getByText('Создание документа…')).toBeInTheDocument()

    resolveCreate({ documentId: 'doc-1', status: 'draft' })

    await waitFor(() => {
      expect(screen.getByText('Черновик, ещё не сохранён')).toBeInTheDocument()
    })
  })
})
