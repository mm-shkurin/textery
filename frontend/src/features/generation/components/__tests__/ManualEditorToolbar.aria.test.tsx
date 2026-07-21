import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

describe('ManualEditorToolbar disclosure semantics (link button)', () => {
  // GREEN today (line 56 already toggles aria-expanded from openUiKey). Kept as a
  // live regression guard so the "drop aria-pressed for UI actions" fix cannot
  // also strip the disclosure state the popover button must expose.
  it('the link button exposes aria-expanded that toggles false→true→false as the popover opens and closes', async () => {
    await renderEditorWithDocumentCreated()

    const link = screen.getByTestId('toolbar-link')
    expect(link).toHaveAttribute('aria-expanded', 'false')

    fireEvent.click(link)
    expect(link).toHaveAttribute('aria-expanded', 'true')

    fireEvent.click(screen.getByTestId('link-cancel'))
    expect(link).toHaveAttribute('aria-expanded', 'false')
  })

  // Defect 6 RESOLVED (design decision 2026-07-21, "keep both"): the link button
  // carries BOTH aria-pressed and aria-expanded because they encode ORTHOGONAL
  // states — aria-pressed = the cursor is inside an existing link (isActive,
  // scenario 7.9's Gherkin, pinned in ManualEditor.link.test.tsx:54/63);
  // aria-expanded = the popover is open. ARIA permits both on one control and
  // they are not in conflict. The original "drop aria-pressed" premise was wrong:
  // it would delete the cursor-in-link indicator, a separate requirement. This
  // guard pins independence — opening the popover flips aria-expanded WITHOUT
  // touching aria-pressed, and both are present throughout.
  it('the link button carries aria-pressed and aria-expanded as independent states', async () => {
    await renderEditorWithDocumentCreated()

    const link = screen.getByTestId('toolbar-link')
    // Selection is plain "hello" (not a link) and the popover is closed.
    expect(link).toHaveAttribute('aria-pressed', 'false')
    expect(link).toHaveAttribute('aria-expanded', 'false')

    // Opening the disclosure flips aria-expanded only; aria-pressed is orthogonal
    // (the selection is still not inside a link) and must stay 'false'.
    fireEvent.click(link)
    expect(link).toHaveAttribute('aria-expanded', 'true')
    expect(link).toHaveAttribute('aria-pressed', 'false')
  })

  // GREEN today — regression guard. The fix must strip aria-pressed from the UI
  // button ONLY, never from the 16 formatting buttons whose pressed state is
  // their whole purpose.
  it('a non-UI formatting button keeps aria-pressed reflecting its inactive state on an empty doc', async () => {
    await renderEditorWithDocumentCreated()

    expect(screen.getByTestId('toolbar-bold')).toHaveAttribute('aria-pressed', 'false')
  })
})

describe('ManualEditorToolbar anchor-span wrapper (only for UI actions)', () => {
  // RED 2026-07-21 (green-frontend-aria owns the fix): line 48 wraps EVERY button
  // in a <span>, an unnecessary DOM wrapper around all 17 buttons. Only the UI
  // (link) button needs the positioning-context span for its popover. After the
  // fix a non-UI button renders bare, so its DOM parent is the toolbar row itself
  // (the .me-toolbar DIV), not any span. Actual: expected 'SPAN' to be 'DIV' —
  // bold's parent is currently a bare span.
  it('a non-UI button sits directly in the me-toolbar row (parent is the DIV, no span wrapper)', async () => {
    await renderEditorWithDocumentCreated()

    const parent = screen.getByTestId('toolbar-bold').parentElement
    expect(parent?.tagName).toBe('DIV')
    expect(parent?.classList.contains('me-toolbar')).toBe(true)
  })

  // GREEN today — regression guard. The link button must STILL sit inside its
  // me-link-popover-anchor span (the popover's positioning context).
  it('the link button stays wrapped in the me-link-popover-anchor span', async () => {
    await renderEditorWithDocumentCreated()

    const parent = screen.getByTestId('toolbar-link').parentElement
    expect(parent?.tagName).toBe('SPAN')
    expect(parent?.classList.contains('me-link-popover-anchor')).toBe(true)
  })
})
