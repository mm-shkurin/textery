import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'

vi.mock('../../api/documentApi')

describe('ManualEditor reopen flow', () => {
  it('reopening an existing document fetches it via getDocument and populates the editor with its saved content and version, without creating a new document', async () => {
    // Safety default so an erroneous createDocument call (current behavior,
    // which ignores existingDocumentId) resolves instead of crashing the
    // effect with "Cannot read properties of undefined (reading 'then')" —
    // that would mask the actual assertion under test.
    vi.mocked(documentApi.createDocument).mockResolvedValue({ documentId: 'doc-1', status: 'draft', version: 7 })
    vi.mocked(documentApi.getDocument).mockResolvedValue({
      documentId: 'doc-99',
      status: 'draft',
      content: '<strong>Saved</strong> content',
      version: 3,
    })

    render(
      <ManualEditor
        documentType="doklad"
        documentTypeLabel="Доклад"
        onBack={vi.fn()}
        existingDocumentId="doc-99"
      />
    )

    await waitFor(() => {
      expect(documentApi.getDocument).toHaveBeenCalledWith('doc-99')
    })
    expect(documentApi.createDocument).not.toHaveBeenCalled()

    const contentArea = await screen.findByTestId('editor-content-area')
    await waitFor(() => {
      expect(contentArea.innerHTML).toBe('<strong>Saved</strong> content')
    })

    vi.mocked(documentApi.saveDocument).mockResolvedValue({ status: 'saved', version: 4, content: '<strong>Saved</strong> content' })
    const saveButton = screen.getByRole('button', { name: 'Сохранить' })
    saveButton.click()

    await waitFor(() => {
      expect(documentApi.saveDocument).toHaveBeenCalledWith('doc-99', '<strong>Saved</strong> content', 3)
    })
  })
})
