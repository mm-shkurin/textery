import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
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

    vi.mocked(documentApi.saveDocument).mockResolvedValue({ status: 'saved', version: 2 })

    const saveButton = screen.getByRole('button', { name: 'Сохранить' })
    fireEvent.click(saveButton)

    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenCalledWith('doc-1', 'hello world', 1)

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

    vi.mocked(documentApi.saveDocument).mockResolvedValue({ status: 'saved', version: 2 })

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
    const savePromise = new Promise<{ status: string; version: number }>((_resolve, reject) => {
      rejectSave = reject
    })
    vi.mocked(documentApi.saveDocument).mockReturnValueOnce(savePromise)

    const saveButton = screen.getByRole('button', { name: 'Сохранить' })
    fireEvent.click(saveButton)

    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    rejectSave(new Error('network error'))

    await waitFor(() => {
      expect(
        screen.getByText(
          'Не удалось сохранить документ. Проверьте соединение и попробуйте ещё раз — введённый текст сохранён локально в редакторе.',
        ),
      ).toBeInTheDocument()
    })
    expect(contentArea.textContent).toBe('hello world')

    const errorBanner = screen.getByText(
      'Не удалось сохранить документ. Проверьте соединение и попробуйте ещё раз — введённый текст сохранён локально в редакторе.',
    )
    expect(errorBanner).toHaveAttribute('role', 'alert')

    consoleErrorSpy.mockRestore()
  })

  it('a stale error banner clears once a subsequent retry save succeeds', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    let rejectSave: (error: Error) => void = () => {}
    const failedSavePromise = new Promise<{ status: string; version: number }>((_resolve, reject) => {
      rejectSave = reject
    })
    vi.mocked(documentApi.saveDocument).mockReturnValueOnce(failedSavePromise)

    const saveButton = screen.getByRole('button', { name: 'Сохранить' })
    fireEvent.click(saveButton)

    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    rejectSave(new Error('network error'))

    const errorMessage =
      'Не удалось сохранить документ. Проверьте соединение и попробуйте ещё раз — введённый текст сохранён локально в редакторе.'

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument()
    })

    vi.mocked(documentApi.saveDocument).mockResolvedValue({ status: 'saved', version: 2 })
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText('Сохранено')).toBeInTheDocument()
    })
    expect(screen.queryByText(errorMessage)).not.toBeInTheDocument()

    consoleErrorSpy.mockRestore()
  })

  it('editing content while a save is in flight, without clicking Сохранить again, still auto-retriggers and never shows a false "Сохранено"', async () => {
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

    // Edit only, no second click, while the first save is still in flight.
    contentArea.textContent = 'second content'
    fireEvent.input(contentArea)

    resolveFirstSave({ status: 'saved', version: 2 })

    await waitFor(() => {
      expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    })
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(2, 'doc-1', 'second content', 2)
    expect(screen.queryByText('Сохранено')).not.toBeInTheDocument()
    expect(screen.getByText('Черновик, ещё не сохранён')).toBeInTheDocument()

    resolveSecondSave({ status: 'saved', version: 3 })

    await waitFor(() => {
      expect(screen.getByText('Сохранено')).toBeInTheDocument()
    })
  })
})
