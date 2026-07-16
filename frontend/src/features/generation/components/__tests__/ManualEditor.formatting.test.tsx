import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderEditorWithDocumentCreated, selectRange } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

describe('ManualEditor formatting toolbar', () => {
  it('applying bold to selected text wraps it in <strong> and marks the bold button active', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    expect(contentArea).toHaveAttribute('contenteditable', 'true')

    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    const textNode = contentArea.firstChild as Node
    selectRange(textNode, 0, 5)
    fireEvent.select(contentArea)

    const boldButton = screen.getByTestId('toolbar-bold')
    fireEvent.click(boldButton)

    expect(contentArea.innerHTML).toBe('<strong>hello</strong> world')
    expect(boldButton).toHaveAttribute('aria-pressed', 'true')
  })

  it('moving the cursor from bold text to non-bold text deactivates the bold toolbar button', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'bold plain'
    fireEvent.input(contentArea)

    const initialTextNode = contentArea.firstChild as Node
    selectRange(initialTextNode, 0, 4)
    fireEvent.select(contentArea)

    const boldButton = screen.getByTestId('toolbar-bold')
    fireEvent.click(boldButton)

    expect(contentArea.innerHTML).toBe('<strong>bold</strong> plain')
    expect(boldButton).toHaveAttribute('aria-pressed', 'true')

    const plainTextNode = contentArea.lastChild as Node
    selectRange(plainTextNode, 1, 1)
    fireEvent.select(contentArea)

    expect(boldButton).toHaveAttribute('aria-pressed', 'false')
    const italicButton = screen.getByLabelText('Курсив')
    expect(italicButton).toHaveAttribute('aria-pressed', 'false')
  })

  it('applying strikethrough to selected text wraps it in <s> and marks the strikethrough button active', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    const textNode = contentArea.firstChild as Node
    selectRange(textNode, 0, 5)
    fireEvent.select(contentArea)

    const strikeButton = screen.getByTestId('toolbar-strike')
    fireEvent.click(strikeButton)

    expect(contentArea.innerHTML).toBe('<s>hello</s> world')
    expect(strikeButton).toHaveAttribute('aria-pressed', 'true')
  })

  it('moving the cursor from strikethrough text to non-strikethrough text deactivates the strikethrough toolbar button', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'struck plain'
    fireEvent.input(contentArea)

    const initialTextNode = contentArea.firstChild as Node
    selectRange(initialTextNode, 0, 6)
    fireEvent.select(contentArea)

    const strikeButton = screen.getByTestId('toolbar-strike')
    fireEvent.click(strikeButton)

    expect(contentArea.innerHTML).toBe('<s>struck</s> plain')
    expect(strikeButton).toHaveAttribute('aria-pressed', 'true')

    const plainTextNode = contentArea.lastChild as Node
    selectRange(plainTextNode, 1, 1)
    fireEvent.select(contentArea)

    expect(strikeButton).toHaveAttribute('aria-pressed', 'false')
  })

  it.skip('applying underline to selected text wraps it in <u> and marks the underline button active', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    const textNode = contentArea.firstChild as Node
    selectRange(textNode, 0, 5)
    fireEvent.select(contentArea)

    const underlineButton = screen.getByTestId('toolbar-underline')
    fireEvent.click(underlineButton)

    expect(contentArea.innerHTML).toBe('<u>hello</u> world')
    expect(underlineButton).toHaveAttribute('aria-pressed', 'true')
  })

  it.skip('moving the cursor from underlined text to non-underlined text deactivates the underline toolbar button', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'under plain'
    fireEvent.input(contentArea)

    const initialTextNode = contentArea.firstChild as Node
    selectRange(initialTextNode, 0, 5)
    fireEvent.select(contentArea)

    const underlineButton = screen.getByTestId('toolbar-underline')
    fireEvent.click(underlineButton)

    expect(contentArea.innerHTML).toBe('<u>under</u> plain')
    expect(underlineButton).toHaveAttribute('aria-pressed', 'true')

    const plainTextNode = contentArea.lastChild as Node
    selectRange(plainTextNode, 1, 1)
    fireEvent.select(contentArea)

    expect(underlineButton).toHaveAttribute('aria-pressed', 'false')
  })
})
