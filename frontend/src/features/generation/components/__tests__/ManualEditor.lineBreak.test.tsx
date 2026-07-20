import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

// Bug: in Ручной режим the text prints on a single line only — a line break
// cannot be made. Root cause: the editor's Document holds `inline*` content
// (no paragraph wrapper) AND StarterKit's hardBreak is disabled, so there is
// no schema node capable of representing a line break. A `<br>` that reaches
// the document is dropped by ProseMirror's schema-driven reconciliation,
// collapsing the two lines into one. This test pins the user-facing contract:
// a hard break survives in the content (so it saves and reopens intact).
// RED 2026-07-20: green is BLOCKED pending an architecture decision. The naive
// fix (re-enable StarterKit hardBreak) reintroduces a real, persisted defect the
// author disabled it for: with this inline* document, ProseMirror's trailing-break
// cursor helper is reparsed by the domObserver into a stray trailing hardBreak
// NODE, so editor.getHTML() (the save payload, useDocumentSave.ts:84) persists an
// extra <br> on every non-empty save, and 32 live-DOM-innerHTML tests regress.
// Representing a line break in an inline*-doc without that corruption is a design
// choice (custom Enter keymap + trailing-break filter vs. block-schema rebuild);
// see the /architecture ADR before un-skipping. Test stays as the executable pin.
describe.skip('ManualEditor line break', () => {
  it('preserves a hard line break so typed text can span multiple lines', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.innerHTML = 'line one<br>line two'
    fireEvent.input(contentArea)

    expect(contentArea.querySelector('br')).not.toBeNull()
    expect(contentArea.innerHTML).toBe('line one<br>line two')
  })
})
