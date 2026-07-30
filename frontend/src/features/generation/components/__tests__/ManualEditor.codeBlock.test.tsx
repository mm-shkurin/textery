import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import {
  paragraphTextNode,
  renderEditorWithDocumentCreated,
  TRAILING_BREAK_P,
} from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

describe('ManualEditor code-block toolbar', () => {
  it('applying a code block with only a collapsed cursor on the line wraps the whole line in <pre><code>', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    const textNode = paragraphTextNode(contentArea)
    const cursorRange = document.createRange()
    cursorRange.setStart(textNode, 3)
    cursorRange.setEnd(textNode, 3)
    const selection = window.getSelection()
    selection?.removeAllRanges()
    selection?.addRange(cursorRange)
    fireEvent.select(contentArea)

    const codeBlockButton = screen.getByTestId('toolbar-code-block')
    fireEvent.click(codeBlockButton)

    // Block schema: codeBlock is a real block node; converting the paragraph
    // leaves an empty trailing paragraph as the cursor's landing block.
    expect(contentArea.innerHTML).toBe(`<pre><code>hello world</code></pre>${TRAILING_BREAK_P}`)
    expect(codeBlockButton).toHaveAttribute('aria-pressed', 'true')
  })
})
