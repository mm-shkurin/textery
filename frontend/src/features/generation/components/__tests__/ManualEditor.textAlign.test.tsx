import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

describe('ManualEditor text-align toolbar', () => {
  // TDD Red Phase - toolbar-align-center not implemented
  it.skip('applying center alignment with only a collapsed cursor on the line wraps the whole line with a centered style', async () => {
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

    const alignCenterButton = screen.getByTestId('toolbar-align-center')
    fireEvent.click(alignCenterButton)

    expect(contentArea.innerHTML).toBe('<div style="text-align: center">hello world</div>')
    expect(alignCenterButton).toHaveAttribute('aria-pressed', 'true')

    const restoredSelection = window.getSelection()
    expect(restoredSelection?.isCollapsed).toBe(true)
    expect(restoredSelection?.anchorOffset).toBe(3)
    expect(restoredSelection?.focusOffset).toBe(3)
  })
})
