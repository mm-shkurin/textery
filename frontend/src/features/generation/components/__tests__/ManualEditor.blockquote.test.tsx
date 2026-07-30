import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import {
  paragraphTextNode,
  renderEditorWithDocumentCreated,
  TRAILING_BREAK_P,
} from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

// Block schema: blockquote is a real block node now, so toggling it wraps the
// whole paragraph the selection sits in (not a partial inline range) in
// <blockquote><p>…</p></blockquote>, and ProseMirror renders an empty trailing
// paragraph as the cursor's landing block after the wrapper.
describe('ManualEditor blockquote toolbar', () => {
  it('applying a blockquote to a paragraph wraps its block in <blockquote> and marks the blockquote button active', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    const textNode = paragraphTextNode(contentArea)
    const range = document.createRange()
    range.setStart(textNode, 0)
    range.setEnd(textNode, 5)
    const selection = window.getSelection()
    selection?.removeAllRanges()
    selection?.addRange(range)
    fireEvent.select(contentArea)

    const blockquoteButton = screen.getByTestId('toolbar-blockquote')
    fireEvent.click(blockquoteButton)

    expect(contentArea.innerHTML).toBe(
      `<blockquote><p>hello world</p></blockquote>${TRAILING_BREAK_P}`,
    )
    expect(blockquoteButton).toHaveAttribute('aria-pressed', 'true')
  })

  it('applying a blockquote with only a collapsed cursor on the line wraps the whole line in <blockquote>', async () => {
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

    const blockquoteButton = screen.getByTestId('toolbar-blockquote')
    fireEvent.click(blockquoteButton)

    expect(contentArea.innerHTML).toBe(
      `<blockquote><p>hello world</p></blockquote>${TRAILING_BREAK_P}`,
    )
    expect(blockquoteButton).toHaveAttribute('aria-pressed', 'true')
  })

  it('applying a blockquote with a collapsed cursor keeps the cursor at its original position instead of selecting the whole line', async () => {
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

    const blockquoteButton = screen.getByTestId('toolbar-blockquote')
    fireEvent.click(blockquoteButton)

    expect(contentArea.innerHTML).toBe(
      `<blockquote><p>hello world</p></blockquote>${TRAILING_BREAK_P}`,
    )

    const restoredSelection = window.getSelection()
    expect(restoredSelection?.isCollapsed).toBe(true)
    expect(restoredSelection?.anchorOffset).toBe(3)
    expect(restoredSelection?.focusOffset).toBe(3)
  })
})
