import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

describe('ManualEditor inline code toolbar', () => {
  // RED (scenario 7.4): inline-code toolbar button does not exist yet
  it.skip('applying inline code to selected text wraps it in <code> and marks the code button active', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    expect(contentArea).toHaveAttribute('contenteditable', 'true')

    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    const textNode = contentArea.firstChild as Node
    const range = document.createRange()
    range.setStart(textNode, 0)
    range.setEnd(textNode, 5)
    const selection = window.getSelection()
    selection?.removeAllRanges()
    selection?.addRange(range)
    fireEvent.select(contentArea)

    const codeButton = screen.getByTestId('toolbar-code')
    fireEvent.click(codeButton)

    expect(contentArea.innerHTML).toBe('<code>hello</code> world')
    expect(codeButton).toHaveAttribute('aria-pressed', 'true')
  })

  // RED (scenario 7.4): inline-code toolbar button does not exist yet
  it.skip('moving the cursor from inline code to non-code text deactivates the code toolbar button', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'coded plain'
    fireEvent.input(contentArea)

    const initialTextNode = contentArea.firstChild as Node
    const codeRange = document.createRange()
    codeRange.setStart(initialTextNode, 0)
    codeRange.setEnd(initialTextNode, 5)
    const selection = window.getSelection()
    selection?.removeAllRanges()
    selection?.addRange(codeRange)
    fireEvent.select(contentArea)

    const codeButton = screen.getByTestId('toolbar-code')
    fireEvent.click(codeButton)

    expect(contentArea.innerHTML).toBe('<code>coded</code> plain')
    expect(codeButton).toHaveAttribute('aria-pressed', 'true')

    const plainTextNode = contentArea.lastChild as Node
    const cursorRange = document.createRange()
    cursorRange.setStart(plainTextNode, 1)
    cursorRange.setEnd(plainTextNode, 1)
    selection?.removeAllRanges()
    selection?.addRange(cursorRange)
    fireEvent.select(contentArea)

    expect(codeButton).toHaveAttribute('aria-pressed', 'false')
  })
})
