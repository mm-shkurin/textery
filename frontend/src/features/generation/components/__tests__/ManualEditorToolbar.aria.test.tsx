import { describe, expect, it } from 'vitest'
import { vi } from 'vitest'
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

  // RED 2026-07-21 (green-frontend-aria owns the fix): line 55 sets aria-pressed
  // on EVERY button, including the link (UI/disclosure) button. A disclosure
  // control must expose aria-expanded only — carrying both is two competing
  // state semantics on one control. Actual: expected element not to have
  // attribute aria-pressed, received aria-pressed="false".
  it.skip('the link button does NOT carry aria-pressed (disclosure state is aria-expanded, not pressed)', async () => {
    await renderEditorWithDocumentCreated()

    expect(screen.getByTestId('toolbar-link')).not.toHaveAttribute('aria-pressed')
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
  it.skip('a non-UI button sits directly in the me-toolbar row (parent is the DIV, no span wrapper)', async () => {
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
