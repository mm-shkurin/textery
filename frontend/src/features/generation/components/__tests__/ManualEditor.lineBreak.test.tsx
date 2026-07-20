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
describe('ManualEditor line break', () => {
  it('preserves a hard line break so typed text can span multiple lines', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.innerHTML = 'line one<br>line two'
    fireEvent.input(contentArea)

    expect(contentArea.querySelector('br')).not.toBeNull()
    expect(contentArea.innerHTML).toBe('line one<br>line two')
  })
})
