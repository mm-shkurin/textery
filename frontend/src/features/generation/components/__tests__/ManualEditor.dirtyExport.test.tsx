import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

// Explicit factory (not auto-mock): exportDocument's runtime mock cannot be attached to the frozen
// ES module namespace after import, so every consumed function is declared here. createDocument is
// driven by renderEditorWithDocumentCreated; saveDocument and exportDocument are configured per test.
vi.mock('../../api/documentApi', () => ({
  createDocument: vi.fn(),
  getDocument: vi.fn(),
  saveDocument: vi.fn(),
  exportDocument: vi.fn(),
}))

describe('ManualEditor dirty export save-first ordering', () => {
  it('saves the document and waits for it to settle before dispatching the export', async () => {
    // A freshly-created editor is dirty (hasUnsavedChanges initializes to true), so exporting must
    // persist first — the export renders STORED html, and shipping before the save resolves would
    // download a stale file (the exact bug scenario 4.1 exists to prevent).
    const callOrder: string[] = []

    // Push 'save' at RESOLUTION time, not at invocation. This distinguishes a genuine
    // await-the-save from a fire-and-forget save that returns void: if the export does not wait for
    // the save's promise to settle, 'export' lands in the array before 'save' and the order fails.
    vi.mocked(documentApi.saveDocument).mockImplementation(async (_id, content, version) => {
      await Promise.resolve()
      callOrder.push('save')
      return { status: 'draft', version, content }
    })
    vi.mocked(documentApi.exportDocument).mockImplementation(async () => {
      callOrder.push('export')
      return new Blob(['pdf'], { type: 'application/pdf' })
    })

    await renderEditorWithDocumentCreated()

    // Give the editor real unsaved text so the stale-file bug is exercised concretely, not just via
    // the mount-time dirty flag: this is the exact string the save-first path must persist before
    // the export renders stored html. The editor runs the StarterKit BLOCK schema (block-schema
    // migration ADR, 2026-07-26), so typed text serializes inside a paragraph — the assertion below
    // pins `<p>unsaved edit</p>`, not the bare string the old inline-Document schema produced.
    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'unsaved edit'
    fireEvent.input(contentArea)

    fireEvent.click(screen.getByTestId('export-control-trigger'))
    fireEvent.click(screen.getByTestId('export-option-pdf'))

    await waitFor(() => expect(documentApi.exportDocument).toHaveBeenCalledTimes(1))
    // Exact args, not just counts: the save must persist the current editor text against the
    // create response's version (7 from renderEditorWithDocumentCreated), and the export must
    // request the created document in the format the user picked.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenCalledWith('doc-1', '<p>unsaved edit</p>', 7)
    expect(documentApi.exportDocument).toHaveBeenCalledWith('doc-1', 'pdf')
    expect(callOrder).toEqual(['save', 'export'])
  })
})
