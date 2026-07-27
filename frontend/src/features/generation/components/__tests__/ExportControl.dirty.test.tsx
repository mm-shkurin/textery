import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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
// RED 4.1: ExportControl does not yet accept `hasUnsavedChanges`/`save` — the dirty-path save-first
// ordering is unimplemented. Un-skip in green-frontend once export awaits save() before dispatch.
describe.skip('ExportControl save-first on dirty export', () => {
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
})
