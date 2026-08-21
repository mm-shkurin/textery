import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'

vi.mock('../../api/documentApi')

describe('ManualEditor heading 3 parseHTML', () => {
  it('loading a saved document containing an existing <h3> restores it as a level-3 Heading node', async () => {
    vi.mocked(documentApi.createDocument).mockResolvedValue({
      documentId: 'doc-1',
      status: 'draft',
      version: 7,
    })
    vi.mocked(documentApi.getDocument).mockResolvedValue({
      documentId: 'doc-99',
      status: 'draft',
      content: 'before<h3>hello world</h3>after',
      version: 3,
    })

    render(
      <ManualEditor
        documentType="doklad"
        documentTypeLabel="Доклад"
        onBack={vi.fn()}
        existingDocumentId="doc-99"
      />,
    )

    await waitFor(() => {
      expect(documentApi.getDocument).toHaveBeenCalledWith('doc-99', expect.any(AbortSignal))
    })

    // Block schema: top-level inline text auto-wraps into paragraphs, and the
    // <h3> parses into a real level-3 Heading NODE sitting between them (the
    // custom Heading3 mark is retired). Root children: <p>before</p>, <h3>, <p>after</p>.
    const contentArea = await screen.findByTestId('editor-content-area')
    await waitFor(() => {
      expect(contentArea.innerHTML).toBe('<p>before</p><h3>hello world</h3><p>after</p>')
    })

    // Place a collapsed cursor inside the restored heading and read the toolbar
    // to pin that the H3 control reflects the level-3 heading node at the cursor.
    const textNode = contentArea.childNodes[1].firstChild as Node
    const range = document.createRange()
    range.setStart(textNode, 1)
    range.setEnd(textNode, 1)
    const selection = window.getSelection()
    selection?.removeAllRanges()
    selection?.addRange(range)
    fireEvent.select(contentArea)

    expect(screen.getByTestId('toolbar-h3')).toHaveAttribute('aria-pressed', 'true')
  })
})
