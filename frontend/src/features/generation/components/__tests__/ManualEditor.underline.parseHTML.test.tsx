import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'
import { selectRange } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

describe('ManualEditor underline parseHTML', () => {
  it('loading a saved document containing an existing <u> restores it as the underline mark', async () => {
    vi.mocked(documentApi.createDocument).mockResolvedValue({ documentId: 'doc-1', status: 'draft', version: 7 })
    vi.mocked(documentApi.getDocument).mockResolvedValue({
      documentId: 'doc-99',
      status: 'draft',
      content: 'before<u>hello</u>after',
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
      expect(documentApi.getDocument).toHaveBeenCalledExactlyOnceWith('doc-99')
    })

    const contentArea = await screen.findByTestId('editor-content-area')
    await waitFor(() => {
      expect(contentArea.innerHTML).toBe('before<u>hello</u>after')
    })

    // innerHTML alone cannot tell an applied Underline mark from raw <u>
    // passthrough - both render byte-identically. Place a collapsed cursor
    // inside the restored text and read the toolbar to pin that the mark
    // actually won the parse.
    const textNode = contentArea.childNodes[1].firstChild as Node
    selectRange(textNode, 1, 1)
    fireEvent.select(contentArea)

    // Underline must be the SOLE winner. Asserting only aria-pressed=true on
    // underline would still pass if a mis-scoped parseHTML rule matched on
    // text-decoration rather than tag name and lit strike too, so every other
    // mark reachable at this cursor is pinned false. horizontal-rule/undo/redo
    // are excluded deliberately: their isActive is hardcoded `() => false`
    // (editorToolbarActions.ts), so asserting them proves nothing.
    expect(screen.getByTestId('toolbar-underline')).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByTestId('toolbar-strike')).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByTestId('toolbar-bold')).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByTestId('toolbar-code')).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByTestId('toolbar-h3')).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByTestId('toolbar-blockquote')).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByTestId('toolbar-code-block')).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByTestId('toolbar-align-center')).toHaveAttribute('aria-pressed', 'false')
  })
})
