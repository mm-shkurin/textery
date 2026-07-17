import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import { SAVE_ERROR_MESSAGE } from '../ManualEditor'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

describe('ManualEditor save status', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('a successful save shows an inline "Сохранено" confirmation and stays on the same editor with no page navigation', async () => {
    const onBack = await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    vi.mocked(documentApi.saveDocument).mockResolvedValue({
      status: 'saved',
      version: 2,
      content: 'hello world',
    })

    const saveButton = screen.getByRole('button', { name: 'Сохранить' })
    fireEvent.click(saveButton)

    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenCalledWith('doc-1', 'hello world', 7)

    await waitFor(() => {
      expect(screen.getByText('Сохранено')).toBeInTheDocument()
    })
    expect(saveButton).toHaveAttribute('aria-disabled', 'false')
    expect(screen.queryByTestId('save-spinner')).not.toBeInTheDocument()
    expect(screen.getByTestId('manual-editor')).toBeInTheDocument()
    expect(onBack).not.toHaveBeenCalled()
  })

  it('editing content again after a successful save reverts the status away from "Сохранено"', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    vi.mocked(documentApi.saveDocument).mockResolvedValue({
      status: 'saved',
      version: 2,
      content: 'hello world',
    })

    const saveButton = screen.getByRole('button', { name: 'Сохранить' })
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText('Сохранено')).toBeInTheDocument()
    })

    contentArea.textContent = 'hello world again'
    fireEvent.input(contentArea)

    expect(screen.queryByText('Сохранено')).not.toBeInTheDocument()
    expect(screen.getByText('Черновик, ещё не сохранён')).toBeInTheDocument()
  })

  it('a failed save shows an inline error message and keeps the typed content in the editor', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    let rejectSave: (error: Error) => void = () => {}
    const savePromise = new Promise<documentApi.SaveDocumentResult>((_resolve, reject) => {
      rejectSave = reject
    })
    vi.mocked(documentApi.saveDocument).mockReturnValueOnce(savePromise)

    const saveButton = screen.getByRole('button', { name: 'Сохранить' })
    fireEvent.click(saveButton)

    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    rejectSave(new Error('network error'))

    await waitFor(() => {
      expect(screen.getByText(SAVE_ERROR_MESSAGE)).toBeInTheDocument()
    })
    expect(contentArea.textContent).toBe('hello world')

    const errorBanner = screen.getByText(SAVE_ERROR_MESSAGE)
    expect(errorBanner).toHaveAttribute('role', 'alert')

    consoleErrorSpy.mockRestore()
  })

  it('a stale error banner clears once a subsequent retry save succeeds', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    let rejectSave: (error: Error) => void = () => {}
    const failedSavePromise = new Promise<documentApi.SaveDocumentResult>((_resolve, reject) => {
      rejectSave = reject
    })
    vi.mocked(documentApi.saveDocument).mockReturnValueOnce(failedSavePromise)

    const saveButton = screen.getByRole('button', { name: 'Сохранить' })
    fireEvent.click(saveButton)

    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    rejectSave(new Error('network error'))

    await waitFor(() => {
      expect(screen.getByText(SAVE_ERROR_MESSAGE)).toBeInTheDocument()
    })

    vi.mocked(documentApi.saveDocument).mockResolvedValue({
      status: 'saved',
      version: 2,
      content: 'hello world',
    })
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText('Сохранено')).toBeInTheDocument()
    })
    expect(screen.queryByText(SAVE_ERROR_MESSAGE)).not.toBeInTheDocument()

    consoleErrorSpy.mockRestore()
  })

  it('editing content while a save is in flight, without clicking Сохранить again, still auto-retriggers and never shows a false "Сохранено"', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'first content'
    fireEvent.input(contentArea)

    let resolveFirstSave: (value: documentApi.SaveDocumentResult) => void = () => {}
    const firstSavePromise = new Promise<documentApi.SaveDocumentResult>((resolve) => {
      resolveFirstSave = resolve
    })
    let resolveSecondSave: (value: documentApi.SaveDocumentResult) => void = () => {}
    const secondSavePromise = new Promise<documentApi.SaveDocumentResult>((resolve) => {
      resolveSecondSave = resolve
    })
    vi.mocked(documentApi.saveDocument)
      .mockReturnValueOnce(firstSavePromise)
      .mockReturnValueOnce(secondSavePromise)

    const saveButton = screen.getByRole('button', { name: 'Сохранить' })
    fireEvent.click(saveButton)

    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)

    // Edit only, no second click, while the first save is still in flight.
    contentArea.textContent = 'second content'
    fireEvent.input(contentArea)

    resolveFirstSave({ status: 'saved', version: 2, content: 'first content' })

    await waitFor(() => {
      expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    })
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(2, 'doc-1', 'second content', 2)
    expect(screen.queryByText('Сохранено')).not.toBeInTheDocument()
    expect(screen.getByText('Черновик, ещё не сохранён')).toBeInTheDocument()

    resolveSecondSave({ status: 'saved', version: 3, content: 'second content' })

    await waitFor(() => {
      expect(screen.getByText('Сохранено')).toBeInTheDocument()
    })
  })
})
