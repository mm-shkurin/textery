import { describe, expect, it, vi } from 'vitest'
import { waitFor } from '@testing-library/react'
import { renderEditorReopeningDocument } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

// Owed jsdom guard (premortem CREDIBLE-low, red-frontend-placeholder-reopen-degenerate,
// 2026-07-23). The sibling reopen tests drive only the CLEAN poles: '' (→ placeholder)
// and rich '<strong>Saved</strong> content' (→ no placeholder). The DEGENERATE boundary
// was unpinned: a saved doc whose content parses to a lone hardBreak, an &nbsp;, or plain
// whitespace. inlinePlaceholder.ts keys the decoration off state.doc.content.size === 0,
// so how ProseMirror parses each degenerate string into the inline* schema decides whether
// the user meets the hint or a blank unlabelled box. These are LIVE CHARACTERIZATION tests
// pinning what the shipped parser + HardBreakNode rules actually do TODAY, not a wish:
//   '<br>'   → bare <br> matches HardBreakNode's `{ tag: 'br' }` rule → a real hardBreak
//              leaf node (size 1) → NO placeholder.
//   '&nbsp;' → parsed as a one-char text node U+00A0 (size 1) → NO placeholder.
//   '   '    → leading/trailing whitespace stripped by the inline parser → 0 nodes
//              (size 0) → placeholder PRESENT (blank box, but labelled with the hint).
// The whitespace case rendering blank-with-hint is benign, not a bug: a whitespace-only
// save is treated as empty and the user still sees the labelled affordance.
describe('ManualEditor placeholder on reopen of degenerate content', () => {
  it('reopening a lone hard break (<br>) parses to a real node and shows NO placeholder', async () => {
    const contentArea = await renderEditorReopeningDocument('<br>')

    await waitFor(() => {
      expect(contentArea.innerHTML).toBe('<br><br class="ProseMirror-trailingBreak">')
    })

    expect(contentArea).not.toHaveClass('is-editor-empty')
    expect(contentArea).not.toHaveAttribute('data-placeholder')
    expect(contentArea).not.toHaveAttribute('aria-placeholder')
  })

  it('reopening a non-breaking space (&nbsp;) parses to a text node and shows NO placeholder', async () => {
    const contentArea = await renderEditorReopeningDocument('&nbsp;')

    await waitFor(() => {
      expect(contentArea.innerHTML).toBe('&nbsp;')
    })

    expect(contentArea).not.toHaveClass('is-editor-empty')
    expect(contentArea).not.toHaveAttribute('data-placeholder')
    expect(contentArea).not.toHaveAttribute('aria-placeholder')
  })

  it('reopening plain whitespace parses to an empty doc and shows the placeholder (blank but labelled)', async () => {
    const contentArea = await renderEditorReopeningDocument('   ')

    await waitFor(() => {
      expect(contentArea).toHaveClass('is-editor-empty')
    })
    expect(contentArea).toHaveClass('is-editor-empty')
    expect(contentArea).toHaveAttribute('data-placeholder', 'Начните печатать…')
    expect(contentArea).toHaveAttribute('aria-placeholder', 'Начните печатать…')
  })
})
