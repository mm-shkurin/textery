import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

describe('ManualEditor heading-3 toolbar', () => {
  it('applying an H3 heading with only a collapsed cursor on the line wraps the whole line in <h3>', async () => {
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

    const heading3Button = screen.getByTestId('toolbar-h3')
    fireEvent.click(heading3Button)

    expect(contentArea.innerHTML).toBe('<h3>hello world</h3>')
    expect(heading3Button).toHaveAttribute('aria-pressed', 'true')

    const restoredSelection = window.getSelection()
    expect(restoredSelection?.isCollapsed).toBe(true)
    expect(restoredSelection?.anchorOffset).toBe(3)
    expect(restoredSelection?.focusOffset).toBe(3)
  })
})
