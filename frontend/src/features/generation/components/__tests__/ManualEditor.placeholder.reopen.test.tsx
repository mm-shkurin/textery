import { describe, expect, it, vi } from 'vitest'
import { waitFor } from '@testing-library/react'
import { renderEditorReopeningDocument } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

// Owed guard (premortem CREDIBLE-2, red-frontend-placeholder-reopen, 2026-07-23).
// The sibling placeholder tests only drive the fresh create-empty path
// (renderEditorWithDocumentCreated). Nothing exercised the REOPEN path
// (existingDocumentId ⇒ useDocumentInit calls getDocument + editor.commands.setContent).
// inlinePlaceholder.ts keys the empty-state decoration off state.doc.content.size,
// recomputed on every state update — so it should be correct on reopen too, but that
// was never pinned. These two LIVE characterization tests pin both polarities:
// reopen-empty (setContent('') ⇒ size 0 ⇒ decoration present) and reopen-with-content
// (setContent(non-empty) ⇒ size > 0 ⇒ decoration absent, guarding against setContent
// re-adding the empty marker and against the placeholder bleeding under real text).
describe('ManualEditor placeholder on reopen', () => {
  it('reopening an EMPTY saved document shows the placeholder attribute, empty-state class, and aria-placeholder', async () => {
    const contentArea = await renderEditorReopeningDocument('')

    await waitFor(() => {
      expect(contentArea).toHaveClass('is-editor-empty')
    })
    expect(contentArea).toHaveAttribute('data-placeholder', 'Начните печатать…')
    expect(contentArea).toHaveAttribute('aria-placeholder', 'Начните печатать…')
  })

  it('reopening a document WITH content shows no placeholder attribute, no empty-state class, and no aria-placeholder', async () => {
    const contentArea = await renderEditorReopeningDocument('<strong>Saved</strong> content')

    // Wait until setContent has applied the saved markup, so the absence assertions
    // run against the populated (size > 0) state rather than the transient empty mount.
    await waitFor(() => {
      expect(contentArea.innerHTML).toBe('<strong>Saved</strong> content')
    })

    expect(contentArea).not.toHaveClass('is-editor-empty')
    expect(contentArea).not.toHaveAttribute('data-placeholder')
    expect(contentArea).not.toHaveAttribute('aria-placeholder')
  })
})
