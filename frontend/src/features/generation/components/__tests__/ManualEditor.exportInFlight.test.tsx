import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
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
  // TDD Red Phase - ExportControl options are not wired to an export call and hold no
  // in-flight lock yet (green-frontend adds both).
  it.skip('sends only one export request when the user clicks export twice before it returns', async () => {
    // A deferred promise that never settles during the test: the first export stays in
    // flight for the duration, so a second click can only be suppressed by an in-flight
    // guard in the component — not by the request having already resolved.
    vi.mocked(documentApi.exportDocument).mockReturnValue(new Promise(() => {}))

    await renderEditorWithDocumentCreated()

    fireEvent.click(screen.getByTestId('export-control-trigger'))
    const pdfOption = screen.getByTestId('export-option-pdf')
    fireEvent.click(pdfOption)
    fireEvent.click(pdfOption)

    expect(documentApi.exportDocument).toHaveBeenCalledTimes(1)
  })
})
