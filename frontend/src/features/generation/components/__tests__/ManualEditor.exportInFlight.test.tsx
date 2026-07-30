import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

// Explicit factory (not auto-mock): exportDocument does not exist on documentApi yet
// (it arrives in red-frontend-api / green-frontend-api). An ES module namespace is frozen,
// so the mock cannot be attached at runtime — it must be declared here. The other three
// functions are what ManualEditor's init/save paths import; createDocument is driven by
// renderEditorWithDocumentCreated.
vi.mock('../../api/documentApi', () => ({
  createDocument: vi.fn(),
  getDocument: vi.fn(),
  saveDocument: vi.fn(),
  exportDocument: vi.fn(),
}))

describe('ManualEditor export in-flight safety', () => {
  it('sends only one export request when the user clicks export twice before it returns', async () => {
    // A deferred promise that never settles during the test: the first export stays in
    // flight for the duration, so a second click can only be suppressed by an in-flight
    // guard in the component — not by the request having already resolved.
    vi.mocked(documentApi.exportDocument).mockReturnValue(new Promise(() => {}))
    // A dirty editor persists BEFORE it exports (scenario 4.1 save-first), and the real save returns
    // a promise. A bare vi.fn() would return undefined, which the awaited save-first path cannot
    // settle — so the export would never dispatch and this test would stall. Resolve it to a
    // persisted-document shape so the save completes and the single export fires.
    vi.mocked(documentApi.saveDocument).mockResolvedValue({
      status: 'draft',
      version: 8,
      content: '',
    })

    await renderEditorWithDocumentCreated()

    fireEvent.click(screen.getByTestId('export-control-trigger'))
    const pdfOption = screen.getByTestId('export-option-pdf')
    fireEvent.click(pdfOption)
    fireEvent.click(pdfOption)

    // The export now dispatches AFTER an async save, so it is no longer synchronous with the click.
    // Intent is unchanged: only ONE export despite the double-click (the in-flight lock, set before
    // the save, suppresses the second).
    await waitFor(() => expect(documentApi.exportDocument).toHaveBeenCalledTimes(1))
    // Exact export args, not just a count: the one dispatched request targets the created document
    // in the chosen format, not some other id/format pair. (Save-count is pinned by the skipped
    // dirtyExport wiring test — asserting it here would fail until ExportControl threads `save`.)
    expect(documentApi.exportDocument).toHaveBeenCalledWith('doc-1', 'pdf')
  })
})
