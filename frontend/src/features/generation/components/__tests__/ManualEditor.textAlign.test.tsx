import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { paragraphTextNode, renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

describe('ManualEditor text-align toolbar', () => {
  it('applying center alignment with only a collapsed cursor on the line centers the whole paragraph', async () => {
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

    const alignCenterButton = screen.getByTestId('toolbar-align-center')
    fireEvent.click(alignCenterButton)

    // Block schema: alignment is a `textAlign` block attribute rendered on the
    // paragraph itself (jsdom re-serialises the style with a trailing semicolon),
    // not a wrapping <div> mark.
    expect(contentArea.innerHTML).toBe('<p style="text-align: center;">hello world</p>')
    expect(alignCenterButton).toHaveAttribute('aria-pressed', 'true')

    const restoredSelection = window.getSelection()
    expect(restoredSelection?.isCollapsed).toBe(true)
    expect(restoredSelection?.anchorOffset).toBe(3)
    expect(restoredSelection?.focusOffset).toBe(3)
  })
})
