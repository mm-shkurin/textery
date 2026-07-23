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

  // Characterization of the RETURN trip (premortem CREDIBLE-1). The sibling test above
  // pins only empty→typed (placeholder drops once). This pins typed→empty: after the
  // user deletes all content back to empty the placeholder attribute AND the
  // is-editor-empty class must be RESTORED. inlinePlaceholder.ts keys emptiness off
  // state.doc.content.size (recomputed on every state update), so the attrs reappear
  // the moment the doc is empty again. It also exercises the HardBreak trailing-break
  // artifact: a truly-empty editor renders <br class="ProseMirror-trailingBreak">, but
  // HardBreakNode keeps that DOM helper out of content.size, so size is a faithful 0.
  it('restores the placeholder attribute and empty-state class after content is deleted back to empty', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')

    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    expect(contentArea).not.toHaveAttribute('data-placeholder')
    expect(contentArea).not.toHaveClass('is-editor-empty')

    contentArea.textContent = ''
    fireEvent.input(contentArea)

    expect(contentArea).toHaveAttribute('data-placeholder', 'Начните печатать…')
    expect(contentArea).toHaveClass('is-editor-empty')
  })

  // a11y guard (premortem CREDIBLE-low, 2026-07-23). The placeholder is painted only
  // via CSS ::before { content: attr(data-placeholder) }, which screen readers announce
  // inconsistently, and data-placeholder carries no accessibility semantics. The
  // contenteditable root exposes no accessible name/hint. inlinePlaceholder.ts must ALSO
  // emit aria-placeholder while empty (tracking emptiness exactly like data-placeholder /
  // is-editor-empty) and drop it when non-empty, so a screen-reader user meets a labelled
  // editor. Skipped until green-frontend-placeholder-aria implements it.
  it.skip('exposes aria-placeholder while empty and drops it after typing', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    expect(contentArea).toHaveAttribute('aria-placeholder', 'Начните печатать…')

    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    expect(contentArea).not.toHaveAttribute('aria-placeholder')
  })
})
