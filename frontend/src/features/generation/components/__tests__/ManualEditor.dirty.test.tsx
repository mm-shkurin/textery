import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import { SAVE_ERROR_MESSAGE } from '../ManualEditor'
import {
  paragraphTextNode,
  renderEditorWithDocumentCreated,
  selectRange,
} from './ManualEditor.testSupport'
import { DIRTY_STATUS, SAVED_STATUS } from './ManualEditor.saveStatus.testSupport'

vi.mock('../../api/documentApi')

// Autosave is stubbed out for this FILE, and the reason is a race rather than a preference.
//
// Both tests below assert `saveDocument` was called exactly ONCE, to prove the dirty flag is what
// re-marks the document rather than a fresh in-flight save. But `fireEvent.input` also arms the
// real 1000 ms autosave debounce (`useAutosave.AUTOSAVE_DEBOUNCE_MS`), and the `waitFor` that
// follows runs on real timers with a 5 s budget (`src/test/setup.ts`, raised because the Tiptap
// chunk takes ~1.4 s under full-suite load and comfortably under 1 s alone). So in a full-suite
// run the debounce fires INSIDE that wait, `useDocumentSave` takes its queued-write branch, and
// the count is 2; run alone the file finishes before 1000 ms and it is 1.
//
// The queued re-save is correct product behaviour — it exists so an edit landing mid-flight is not
// marked clean, and it carries the advanced version, so nothing is lost. The defect was the test
// asserting a call count over a window whose length machine load decides. Neither test here is
// about autosave: they drive the «Сохранить» button. Removing the timer makes the count mean what
// the assertions say it means. The autosave suites test the debounce on their own fixture.
vi.mock('../../hooks/useAutosave', () => ({
  AUTOSAVE_DEBOUNCE_MS: 1000,
  useAutosave: () => () => {},
}))

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
    expect(documentApi.saveDocument).toHaveBeenCalledWith('doc-1', '<p>hello world</p>', 7)

    // The document must be observed clean BEFORE the toolbar click: hasUnsavedChanges
    // initialises to true, so without a settled save the final assertion would pass
    // for the wrong reason. getByText (not queryByText) inside waitFor is what makes
    // this gate real — it throws until the save settles, so the gate cannot pass
    // vacuously.
    await waitFor(() => {
      expect(screen.getByText(SAVED_STATUS)).toBeInTheDocument()
    })
    expect(screen.queryByText(DIRTY_STATUS)).not.toBeInTheDocument()

    const textNode = paragraphTextNode(contentArea)
    selectRange(textNode, 0, 5)
    fireEvent.select(contentArea)

    fireEvent.click(screen.getByTestId('toolbar-bold'))

    // Rules out a stored-marks false positive: a collapsed/lost selection would leave
    // toggleMark setting only storedMarks, the document unchanged at 'hello world',
    // and a clean status legitimately correct. This pins the document as genuinely
    // diverged from the saved 'hello world' above, so "Сохранено" cannot be correct.
    expect(contentArea.innerHTML).toBe('<p><strong>hello</strong> world</p>')

    // No second save fired, so the dirty status below can only come from the flag —
    // not from a fresh in-flight save incidentally re-dirtying the document.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)

    expect(screen.getByText(DIRTY_STATUS)).toBeInTheDocument()
    expect(screen.queryByText(SAVED_STATUS)).not.toBeInTheDocument()
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
    expect(documentApi.saveDocument).toHaveBeenCalledWith('doc-1', '<p>hello world</p>', 7)

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

    expect(screen.getByText(DIRTY_STATUS)).toBeInTheDocument()
    expect(screen.queryByText(SAVED_STATUS)).not.toBeInTheDocument()
  })
})
