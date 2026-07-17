import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

describe('ManualEditor save flow', () => {
  // Each test sets up its own saveDocument/createDocument mock resolutions;
  // without a per-test reset, call counts from prior tests in this file
  // (e.g. how many times saveDocument was called) leak into the next test's
  // toHaveBeenCalledTimes assertions.
  afterEach(() => {
    vi.clearAllMocks()
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
    expect(documentApi.saveDocument).toHaveBeenCalledWith('doc-1', 'hello world', 7)

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
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(1, 'doc-1', 'first content', 7)

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
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(2, 'doc-1', 'second content', 7)

    consoleErrorSpy.mockRestore()
  })

})
