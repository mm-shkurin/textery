import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

describe('ManualEditor blockquote toolbar', () => {
  it('applying a blockquote to selected text wraps it in <blockquote> and marks the blockquote button active', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
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

    const blockquoteButton = screen.getByTestId('toolbar-blockquote')
    fireEvent.click(blockquoteButton)

    expect(contentArea.innerHTML).toBe('<blockquote>hello</blockquote> world')
    expect(blockquoteButton).toHaveAttribute('aria-pressed', 'true')
  })

  it('applying a blockquote with only a collapsed cursor on the line wraps the whole line in <blockquote>', async () => {
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

    const blockquoteButton = screen.getByTestId('toolbar-blockquote')
    fireEvent.click(blockquoteButton)

    expect(contentArea.innerHTML).toBe('<blockquote>hello world</blockquote>')
    expect(blockquoteButton).toHaveAttribute('aria-pressed', 'true')
  })

  it.skip('applying a blockquote with a collapsed cursor restores the cursor to its original position instead of leaving the whole line selected', async () => {
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

    const blockquoteButton = screen.getByTestId('toolbar-blockquote')
    fireEvent.click(blockquoteButton)

    expect(contentArea.innerHTML).toBe('<blockquote>hello world</blockquote>')

    const restoredSelection = window.getSelection()
    expect(restoredSelection?.isCollapsed).toBe(true)
    expect(restoredSelection?.anchorOffset).toBe(3)
    expect(restoredSelection?.focusOffset).toBe(3)
  })
})
