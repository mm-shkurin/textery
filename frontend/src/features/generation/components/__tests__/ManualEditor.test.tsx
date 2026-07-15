import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

describe('ManualEditor', () => {
  it('applying bold to selected text wraps it in <strong> and marks the bold button active', async () => {
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
    const boldRange = document.createRange()
    boldRange.setStart(initialTextNode, 0)
    boldRange.setEnd(initialTextNode, 4)
    const selection = window.getSelection()
    selection?.removeAllRanges()
    selection?.addRange(boldRange)
    fireEvent.select(contentArea)

    const boldButton = screen.getByTestId('toolbar-bold')
    fireEvent.click(boldButton)

    expect(contentArea.innerHTML).toBe('<strong>bold</strong> plain')
    expect(boldButton).toHaveAttribute('aria-pressed', 'true')

    const plainTextNode = contentArea.lastChild as Node
    const cursorRange = document.createRange()
    cursorRange.setStart(plainTextNode, 1)
    cursorRange.setEnd(plainTextNode, 1)
    selection?.removeAllRanges()
    selection?.addRange(cursorRange)
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
    const range = document.createRange()
    range.setStart(textNode, 0)
    range.setEnd(textNode, 5)
    const selection = window.getSelection()
    selection?.removeAllRanges()
    selection?.addRange(range)
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
    const strikeRange = document.createRange()
    strikeRange.setStart(initialTextNode, 0)
    strikeRange.setEnd(initialTextNode, 6)
    const selection = window.getSelection()
    selection?.removeAllRanges()
    selection?.addRange(strikeRange)
    fireEvent.select(contentArea)

    const strikeButton = screen.getByTestId('toolbar-strike')
    fireEvent.click(strikeButton)

    expect(contentArea.innerHTML).toBe('<s>struck</s> plain')
    expect(strikeButton).toHaveAttribute('aria-pressed', 'true')

    const plainTextNode = contentArea.lastChild as Node
    const cursorRange = document.createRange()
    cursorRange.setStart(plainTextNode, 1)
    cursorRange.setEnd(plainTextNode, 1)
    selection?.removeAllRanges()
    selection?.addRange(cursorRange)
    fireEvent.select(contentArea)

    expect(strikeButton).toHaveAttribute('aria-pressed', 'false')
  })

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

  it('creates the document on mount and flips save status once creation resolves', async () => {
    let resolveCreate: (value: { documentId: string; status: string }) => void = () => {}
    const createPromise = new Promise<{ documentId: string; status: string }>((resolve) => {
      resolveCreate = resolve
    })
    vi.mocked(documentApi.createDocument).mockReturnValue(createPromise)

    render(<ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={vi.fn()} />)

    expect(documentApi.createDocument).toHaveBeenCalledWith('doklad')
    expect(screen.getByText('Создание документа…')).toBeInTheDocument()

    resolveCreate({ documentId: 'doc-1', status: 'draft' })

    await waitFor(() => {
      expect(screen.getByText('Черновик, ещё не сохранён')).toBeInTheDocument()
    })
  })
})
