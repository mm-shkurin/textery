import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'

vi.mock('../../api/documentApi')

describe('ManualEditor heading 3 parseHTML', () => {
  it('loading a saved document containing an existing <h3> restores it as the heading3 mark, not a Heading node', async () => {
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
      expect(documentApi.getDocument).toHaveBeenCalledWith('doc-99')
    })

    const contentArea = await screen.findByTestId('editor-content-area')
    await waitFor(() => {
      expect(contentArea.innerHTML).toBe('before<h3>hello world</h3>after')
    })

    // StarterKit's Heading node is still registered (ManualEditor.tsx does not
    // disable it) and its parseHTML also matches <h3>, so the innerHTML above
    // is byte-identical whether the mark or the node won the parse. Pin which
    // one applied - same discrimination the inline-code/code-block pair needs.
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
