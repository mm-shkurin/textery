import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

// Bug (Story 05, scenario 2.1): a freshly-created empty ManualEditor shows NO
// placeholder text. Root cause: ManualEditor.tsx:86 configures
// Placeholder.configure({ placeholder: 'Начните печатать…' }), but line 78 sets the
// doc schema to Document.extend({ content: 'inline*' }). Tiptap's stock Placeholder
// extension decorates empty BLOCK nodes; an inline-only schema has no paragraph node,
// so the extension silently no-ops. The empty editor renders exactly
// <br class="ProseMirror-trailingBreak"> — no data-placeholder attribute, no
// is-editor-empty class. The .me-placeholder CSS (ManualEditor.css:41) exists but
// nothing renders it.
//
// RED contract (DOM-observable in jsdom): on a fresh empty editor the content area
// (data-testid="editor-content-area", the ProseMirror root) must carry
// data-placeholder="Начните печатать…" AND the empty-state marker class
// is-editor-empty; after typing, both must be gone (placeholder shows only while
// empty). The CSS ::before visual paint of the attribute is NOT jsdom-observable and
// is deliberately out of scope here (owed to green-selenium) — this test asserts the
// attribute/class presence, which jsdom can see.
//
describe('ManualEditor placeholder', () => {
  it('shows the placeholder attribute and empty-state class while empty, and drops both after typing', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    expect(contentArea).toHaveAttribute('data-placeholder', 'Начните печатать…')
    expect(contentArea).toHaveClass('is-editor-empty')

    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    expect(contentArea).not.toHaveAttribute('data-placeholder')
    expect(contentArea).not.toHaveClass('is-editor-empty')
  })
})
