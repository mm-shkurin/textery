import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  fireEvent,
  render,
  screen,
  waitFor,
  waitForElementToBeRemoved,
} from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import { ExportControl } from '../ExportControl'

// exportDocument is the only runtime import ExportControl pulls from documentApi; an ES module
// namespace is frozen, so the mock must be declared via an explicit factory.
vi.mock('../../api/documentApi', () => ({
  exportDocument: vi.fn(),
}))

function triggerExport() {
  fireEvent.click(screen.getByTestId('export-control-trigger'))
  fireEvent.click(screen.getByTestId('export-option-pdf'))
}

// Scenario 4.1 (SAVE-FIRST): export renders the STORED html, so unsaved edits would ship a stale
// file. When the editor is dirty, the control must persist the edits (save()) and only fire the
// export GET AFTER that save resolves; when clean, it exports directly with no save. These pin the
// ordering at the component level — ExportControl will accept `hasUnsavedChanges` + `save` props.
describe('ExportControl save-first on dirty export', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('saves first and dispatches the export only after the save resolves when there are unsaved edits', async () => {
    // The export stays in flight forever so its presence can only come from a real dispatch, not a
    // settle; the save is a manually-resolvable deferred so we control the ordering window.
    vi.mocked(documentApi.exportDocument).mockReturnValue(new Promise(() => {}))
    let resolveSave: () => void = () => {}
    const save = vi.fn(() => new Promise<void>((resolve) => {
      resolveSave = resolve
    }))

    render(<ExportControl documentId="doc-1" hasUnsavedChanges save={save} />)
    triggerExport()

    // Rising edge: the save fires, but the export must WAIT for it — nothing dispatched yet.
    expect(save).toHaveBeenCalledTimes(1)
    expect(documentApi.exportDocument).not.toHaveBeenCalled()

    // Falling edge: once the save resolves, the export dispatches with the same id + format.
    resolveSave()
    await waitFor(() =>
      expect(documentApi.exportDocument).toHaveBeenCalledTimes(1),
    )
    expect(documentApi.exportDocument).toHaveBeenNthCalledWith(1, 'doc-1', 'pdf')
  })

  it('dispatches the export directly without saving when there are no unsaved edits', () => {
    vi.mocked(documentApi.exportDocument).mockReturnValue(new Promise(() => {}))
    const save = vi.fn(() => Promise.resolve())

    render(<ExportControl documentId="doc-1" hasUnsavedChanges={false} save={save} />)
    triggerExport()

    // Clean path — no regression: the stored html is already current, so no save runs and the
    // export fires straight through with the exact id + format.
    expect(save).not.toHaveBeenCalled()
    expect(documentApi.exportDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.exportDocument).toHaveBeenNthCalledWith(1, 'doc-1', 'pdf')
  })

  // Guard C — ExportControl.tsx:74 (the `catch { return }` inside handleExport's run()). A dirty
  // export whose save REJECTS must (1) NOT dispatch exportDocument — a failed save must never ship
  // the stale stored html — and (2) NOT raise the generic export-error banner, so useDocumentSave's
  // accurate data-loss banner (SessionExpired / VersionConflict) speaks unmasked. This pins that
  // branch: without the `return`, either the export would fire on a rejected save or the generic
  // banner would appear.
  it('skips the export and shows no generic export banner when the save rejects on a dirty export', async () => {
    vi.mocked(documentApi.exportDocument).mockReturnValue(new Promise(() => {}))
    let rejectSave: (reason?: unknown) => void = () => {}
    const save = vi.fn(() => new Promise<void>((_, reject) => {
      rejectSave = reject
    }))

    render(<ExportControl documentId="doc-1" hasUnsavedChanges save={save} />)
    triggerExport()

    expect(save).toHaveBeenCalledTimes(1)

    // The rejection settles the run() chain via the inner catch's `return`; the in-flight lock
    // clears in `finally`, so the spinner's removal is the marker that the whole chain is done.
    rejectSave(new Error('save failed'))
    await waitForElementToBeRemoved(() => screen.queryByTestId('export-spinner'))

    // Stale file never shipped, and no generic banner masks the accurate save-error message.
    expect(documentApi.exportDocument).not.toHaveBeenCalled()
    expect(screen.queryByTestId('export-error')).toBeNull()
  })
})
