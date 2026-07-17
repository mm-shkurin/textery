import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import { SAVE_ERROR_MESSAGE } from '../ManualEditor'
import { renderEditorWithDocumentCreated, selectRange } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

describe('ManualEditor dirty flag', () => {
  afterEach(() => {
    // restoreAllMocks (not just clearAllMocks) so a console.error spy survives no
    // longer than its own test: a spy installed mid-test is never restored if an
    // assertion between the spyOn and the restore throws.
    vi.restoreAllMocks()
    vi.clearAllMocks()
  })

  // Toolbar actions dispatch programmatic ProseMirror transactions, which emit no DOM `input`
  // event. While the dirty flag hung off `input`, this was a live bug parked behind it.skip:
  // formatting a paragraph after a save left the status reading "Сохранено" over unsent markup.
  // The flag now lives on Tiptap's `onUpdate`, which sees typing and programmatic changes alike.
  it('applying a toolbar format after a successful save marks the document unsaved again', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    vi.mocked(documentApi.saveDocument).mockResolvedValue({
      status: 'saved',
      version: 2,
      content: 'hello world',
    })

    fireEvent.click(screen.getByRole('button', { name: 'Сохранить' }))

    // Pins what the server now holds: the clean status below is only meaningful if
    // the save that produced it carried the pre-format content at the known version.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenCalledWith('doc-1', 'hello world', 7)

    // The document must be observed clean BEFORE the toolbar click: hasUnsavedChanges
    // initialises to true, so without a settled save the final assertion would pass
    // for the wrong reason. getByText (not queryByText) inside waitFor is what makes
    // this gate real — it throws until the save settles, so the gate cannot pass
    // vacuously.
    await waitFor(() => {
      expect(screen.getByText('Сохранено')).toBeInTheDocument()
    })
    expect(screen.queryByText('Черновик, ещё не сохранён')).not.toBeInTheDocument()

    const textNode = contentArea.firstChild as Node
    selectRange(textNode, 0, 5)
    fireEvent.select(contentArea)

    fireEvent.click(screen.getByTestId('toolbar-bold'))

    // Rules out a stored-marks false positive: a collapsed/lost selection would leave
    // toggleMark setting only storedMarks, the document unchanged at 'hello world',
    // and a clean status legitimately correct. This pins the document as genuinely
    // diverged from the saved 'hello world' above, so "Сохранено" cannot be correct.
    expect(contentArea.innerHTML).toBe('<strong>hello</strong> world')

    // No second save fired, so the dirty status below can only come from the flag —
    // not from a fresh in-flight save incidentally re-dirtying the document.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)

    expect(screen.getByText('Черновик, ещё не сохранён')).toBeInTheDocument()
    expect(screen.queryByText('Сохранено')).not.toBeInTheDocument()
  })

  it('a failed save leaves the document marked unsaved', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    let rejectSave: (error: Error) => void = () => {}
    const savePromise = new Promise<documentApi.SaveDocumentResult>((_resolve, reject) => {
      rejectSave = reject
    })
    vi.mocked(documentApi.saveDocument).mockReturnValueOnce(savePromise)

    fireEvent.click(screen.getByRole('button', { name: 'Сохранить' }))

    // Pins that a save was genuinely attempted with the typed content: without this
    // an early return in handleSave would leave the document dirty by never having
    // saved at all, and the assertions below would pass for the wrong reason.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenCalledWith('doc-1', 'hello world', 7)

    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const saveError = new Error('network error')
    rejectSave(saveError)

    await waitFor(() => {
      expect(screen.getByText(SAVE_ERROR_MESSAGE)).toBeInTheDocument()
    })

    // The rejection reached the catch branch — the dirty status below follows a real
    // failure, not a save that silently never settled.
    expect(consoleErrorSpy).toHaveBeenCalledWith('Failed to save document', saveError)
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)

    expect(screen.getByText('Черновик, ещё не сохранён')).toBeInTheDocument()
    expect(screen.queryByText('Сохранено')).not.toBeInTheDocument()
  })
})
