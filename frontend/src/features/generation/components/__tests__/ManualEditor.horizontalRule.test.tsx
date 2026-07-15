import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

// RED: toolbar-horizontal-rule button does not exist yet (no horizontalRule entry in TOOLBAR_ACTIONS)
describe.skip('ManualEditor horizontal rule toolbar', () => {
  it('clicking the horizontal-rule toolbar button inserts a divider at the cursor position', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    const textNode = contentArea.firstChild as Node
    const cursorRange = document.createRange()
    cursorRange.setStart(textNode, 5)
    cursorRange.setEnd(textNode, 5)
    const selection = window.getSelection()
    selection?.removeAllRanges()
    selection?.addRange(cursorRange)
    fireEvent.select(contentArea)

    const horizontalRuleButton = screen.getByTestId('toolbar-horizontal-rule')
    fireEvent.click(horizontalRuleButton)

    expect(contentArea.innerHTML).toBe('hello<hr> world')
  })
})
