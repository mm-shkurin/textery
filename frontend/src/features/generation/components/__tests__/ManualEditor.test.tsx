import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'

vi.mock('../../api/documentApi')

async function renderEditorWithDocumentCreated() {
  vi.mocked(documentApi.createDocument).mockResolvedValue({ documentId: 'doc-1', status: 'draft' })
  render(<ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={vi.fn()} />)
  await waitFor(() => {
    expect(screen.getByText('Черновик, ещё не сохранён')).toBeInTheDocument()
  })
}

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

  it('clicking Сохранить shows a loading state, disables the button, and ignores a second click while in flight', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    let resolveSave: (value: { status: string; version: number }) => void = () => {}
    const savePromise = new Promise<{ status: string; version: number }>((resolve) => {
      resolveSave = resolve
    })
    vi.mocked(documentApi.saveDocument).mockReturnValue(savePromise)

    const saveButton = screen.getByRole('button', { name: 'Сохранить' })
    fireEvent.click(saveButton)

    expect(saveButton).toBeDisabled()
    expect(screen.getByTestId('save-spinner')).toBeInTheDocument()

    fireEvent.click(saveButton)

    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenCalledWith('doc-1', 'hello world', 1)

    resolveSave({ status: 'saved', version: 2 })
  })
})
