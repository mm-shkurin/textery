import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'

vi.mock('../../api/documentApi')

describe('ManualEditor code block parseHTML', () => {
  it.skip('loading a saved document containing an existing <pre><code> restores the code block in the editor', async () => {
    vi.mocked(documentApi.createDocument).mockResolvedValue({ documentId: 'doc-1', status: 'draft' })
    vi.mocked(documentApi.getDocument).mockResolvedValue({
      documentId: 'doc-99',
      status: 'draft',
      content: 'before<pre><code>hello world</code></pre>after',
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

    const contentArea = await screen.findByTestId('editor-content-area')
    await waitFor(() => {
      expect(contentArea.innerHTML).toBe('before<pre><code>hello world</code></pre>after')
    })
  })
})
