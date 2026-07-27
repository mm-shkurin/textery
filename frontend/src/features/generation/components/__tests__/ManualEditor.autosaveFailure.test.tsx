import { describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { SAVE_ERROR_MESSAGE } from '../../hooks/useDocumentSave'
import * as documentApi from '../../api/documentApi'
import {
  CREATED_DOCUMENT_ID,
  CREATED_VERSION,
  renderCreatedDocument,
  typeAndFireAutosave,
  useAutosaveFailureFakeTimers,
} from './ManualEditor.autosave.testSupport'

vi.mock('../../api/documentApi')

// Scenario E3.2 (07_Editor_Extension_Tests.md §3.2): a failed AUTOSAVE keeps the content and shows
// the failure. This is a LIVE characterization guard, not a red→green cycle: the autosave path
// (useAutosave.scheduleAutosave) fires the SAME save() from useDocumentSave that a manual click
// fires, whose .catch sets the failed-save banner (setSaveError) and never touches editor content.
// The manual-save failure copy is already tested (ManualEditor.saveFailureKinds/save.test); what
// no test yet pinned is that a debounce-triggered save (no click) surfaces the same failure state
// AND preserves the typed text. This locks that combination in. Debounce interval (AUTOSAVE_DEBOUNCE_MS)
// is the shared E3.1 constant.

describe('ManualEditor — a failed autosave keeps the content and shows the failure (E3.2)', () => {
  // The banner is the assertion; the console.error beside it in the save .catch is this app's only
  // diagnostic and would otherwise print a real-looking failure into a passing run.
  useAutosaveFailureFakeTimers()

  it('shows the failed-save banner and does not clear the editor content when a debounced autosave rejects', async () => {
    await renderCreatedDocument()

    vi.mocked(documentApi.saveDocument).mockRejectedValue(new Error('network down'))

    // Cross the debounce boundary: the autosave fires with no click, then rejects.
    await typeAndFireAutosave('hello world')

    // The autosave was the ONLY trigger — no Сохранить click anywhere in this test.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenCalledWith(
      CREATED_DOCUMENT_ID,
      '<p>hello world</p>',
      CREATED_VERSION,
    )

    // (b) A failed-save state is shown: the banner carries the network-default copy.
    const banner = screen.getByTestId('me-save-error')
    expect(banner).toHaveTextContent(SAVE_ERROR_MESSAGE)

    // (a) The editor content is NOT cleared: the typed paragraph survives the failed autosave,
    // byte-for-byte. Exact innerHTML, not a `contains`: a loose match would still pass if the
    // failure path replaced the content with unrelated markup that happened to embed the phrase.
    expect(screen.getByTestId('editor-content-area').innerHTML).toBe('<p>hello world</p>')
  })
})
