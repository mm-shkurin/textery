import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

describe('ManualEditor code-block toolbar', () => {
  // TDD Red Phase - toolbar-code-block button not implemented
  it.skip('applying a code block with only a collapsed cursor on the line wraps the whole line in <pre><code>', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    const textNode = contentArea.firstChild as Node
    const cursorRange = document.createRange()
    cursorRange.setStart(textNode, 3)
    cursorRange.setEnd(textNode, 3)
    const selection = window.getSelection()
    selection?.removeAllRanges()
    selection?.addRange(cursorRange)
    fireEvent.select(contentArea)

    const codeBlockButton = screen.getByTestId('toolbar-code-block')
    fireEvent.click(codeBlockButton)

    expect(contentArea.innerHTML).toBe('<pre><code>hello world</code></pre>')
    expect(codeBlockButton).toHaveAttribute('aria-pressed', 'true')
  })
})
