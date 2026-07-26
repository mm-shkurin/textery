import { describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, screen } from '@testing-library/react'
import {
  paragraphTextNode,
  renderEditorWithDocumentCreated,
  selectRange,
  TRAILING_BREAK_P,
} from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

// Scenario E2.1 (07_Editor_Extension_Tests §2.1): bulleted and numbered lists
// round-trip. The block-schema migration (ADR 2026-07-26) already enabled the
// StarterKit bulletList/orderedList/listItem nodes, so LOADING <ul>/<ol> HTML
// round-trips as semantic elements (probed: <li> content wraps in <p>). The
// remaining gap is the CREATION path: the toolbar exposes no list controls, so
// a user cannot turn a paragraph into a list in the first place. This pins the
// two toolbar controls that wrap the selected block in the correct list node.
describe('ManualEditor list toolbar', () => {
  // Fresh render → seed a paragraph → put the cursor in it → click the named
  // list control. Returns the content area so the caller can assert the exact
  // resulting block structure. cleanup() before each so the two independent
  // list flows do not leave duplicate editors mounted.
  function applyListControl(ariaLabel: string): HTMLElement {
    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'grocery item'
    fireEvent.input(contentArea)

    selectRange(paragraphTextNode(contentArea), 0, 0)
    fireEvent.select(contentArea)

    fireEvent.click(screen.getByLabelText(ariaLabel))
    return contentArea
  }

  it('exposes bulleted and numbered list controls that wrap the current block in the correct list node', async () => {
    await renderEditorWithDocumentCreated()
    const bulleted = applyListControl('Маркированный список')
    expect(bulleted.innerHTML).toBe(
      `<ul><li><p>grocery item</p></li></ul>${TRAILING_BREAK_P}`,
    )
    expect(screen.getByLabelText('Маркированный список')).toHaveAttribute(
      'aria-pressed',
      'true',
    )

    cleanup()

    await renderEditorWithDocumentCreated()
    const numbered = applyListControl('Нумерованный список')
    expect(numbered.innerHTML).toBe(
      `<ol><li><p>grocery item</p></li></ol>${TRAILING_BREAK_P}`,
    )
    expect(screen.getByLabelText('Нумерованный список')).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })
})
