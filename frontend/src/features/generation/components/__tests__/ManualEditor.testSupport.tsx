import { expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'

export async function renderEditorWithDocumentCreated(onBack = vi.fn()) {
  vi.mocked(documentApi.createDocument).mockResolvedValue({ documentId: 'doc-1', status: 'draft' })
  render(<ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={onBack} />)
  await waitFor(() => {
    expect(screen.getByText('Черновик, ещё не сохранён')).toBeInTheDocument()
  })
  return onBack
}
