import { afterEach, describe, expect, it, vi } from 'vitest'
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
  // Each test sets up its own saveDocument/createDocument mock resolutions;
  // without a per-test reset, call counts from prior tests in this file
  // (e.g. how many times saveDocument was called) leak into the next test's
  // toHaveBeenCalledTimes assertions.
  afterEach(() => {
    vi.clearAllMocks()
  })

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

    expect(saveButton).toHaveAttribute('aria-disabled', 'true')
    expect(screen.getByTestId('save-spinner')).toBeInTheDocument()

    fireEvent.click(saveButton)

    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenCalledWith('doc-1', 'hello world', 1)

    resolveSave({ status: 'saved', version: 2 })
  })

  it('a save requested while one is in flight auto-retriggers with the latest content once the first save resolves, and the button only re-enables after the second settles', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'first content'
    fireEvent.input(contentArea)

    let resolveFirstSave: (value: { status: string; version: number }) => void = () => {}
    const firstSavePromise = new Promise<{ status: string; version: number }>((resolve) => {
      resolveFirstSave = resolve
    })
    let resolveSecondSave: (value: { status: string; version: number }) => void = () => {}
    const secondSavePromise = new Promise<{ status: string; version: number }>((resolve) => {
      resolveSecondSave = resolve
    })
    vi.mocked(documentApi.saveDocument)
      .mockReturnValueOnce(firstSavePromise)
      .mockReturnValueOnce(secondSavePromise)

    const saveButton = screen.getByRole('button', { name: 'Сохранить' })
    fireEvent.click(saveButton)

    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(1, 'doc-1', 'first content', 1)

    contentArea.textContent = 'second content'
    fireEvent.input(contentArea)
    fireEvent.click(saveButton)

    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)

    resolveFirstSave({ status: 'saved', version: 2 })

    await waitFor(() => {
      expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    })
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(2, 'doc-1', 'second content', 2)
    expect(saveButton).toHaveAttribute('aria-disabled', 'true')
    expect(screen.getByTestId('save-spinner')).toBeInTheDocument()

    resolveSecondSave({ status: 'saved', version: 3 })

    await waitFor(() => {
      expect(saveButton).toHaveAttribute('aria-disabled', 'false')
    })
    expect(screen.queryByTestId('save-spinner')).not.toBeInTheDocument()
  })

  it('a save requested while one is in flight is dropped (not retried) if the in-flight save rejects, and the button re-enables for a manual retry', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'first content'
    fireEvent.input(contentArea)

    let rejectFirstSave: (error: Error) => void = () => {}
    const firstSavePromise = new Promise<{ status: string; version: number }>((_resolve, reject) => {
      rejectFirstSave = reject
    })
    vi.mocked(documentApi.saveDocument).mockReturnValueOnce(firstSavePromise)

    const saveButton = screen.getByRole('button', { name: 'Сохранить' })
    fireEvent.click(saveButton)

    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)

    contentArea.textContent = 'second content'
    fireEvent.input(contentArea)
    fireEvent.click(saveButton)

    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)

    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    rejectFirstSave(new Error('network error'))

    await waitFor(() => {
      expect(saveButton).toHaveAttribute('aria-disabled', 'false')
    })
    expect(screen.queryByTestId('save-spinner')).not.toBeInTheDocument()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(consoleErrorSpy).toHaveBeenCalledTimes(1)
    expect(consoleErrorSpy).toHaveBeenCalledWith('Failed to save document', new Error('network error'))

    fireEvent.click(saveButton)
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(2, 'doc-1', 'second content', 1)

    consoleErrorSpy.mockRestore()
  })
})
