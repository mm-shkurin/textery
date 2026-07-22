import { expect } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderEditorWithDocumentCreated, selectRange } from './ManualEditor.testSupport'

// Renders a fresh editor, selects "hello" out of "hello world", opens the link
// popover, types `url` and presses Применить. Returns the content area so each
// test asserts on the resulting anchor. A helper rather than inline setup
// because the URL shapes differ in exactly one value — the URL — and that
// difference is the whole point of the files that use it.
//
// Promoted here from ManualEditor.link.urlShapes.test.tsx (where a comment
// recorded it as deliberately local) once red-frontend-url-shapes-2 added a
// second consumer. That comment's reason still holds for the file it named:
// ManualEditor.link.test.tsx drives the same popover but asserts *within* the
// flow (popover in the document, full attribute set, aria-pressed toggling on
// cursor move), so it still cannot be expressed as a call to this.
export async function applyLinkUrl(url: string) {
  const contentArea = await openLinkPopover()

  fireEvent.change(screen.getByTestId('link-url-input'), { target: { value: url } })
  fireEvent.click(screen.getByTestId('link-apply'))

  return contentArea
}

// Renders a fresh editor, selects "hello" out of "hello world", and opens the
// link popover WITHOUT applying — the seam applyLinkUrl stops short of, for the
// interaction-contract tests that drive the popover's own keys, click-outside,
// and captured range rather than the resulting anchor.
export async function openLinkPopover() {
  await renderEditorWithDocumentCreated()

  const contentArea = screen.getByTestId('editor-content-area')
  contentArea.textContent = 'hello world'
  fireEvent.input(contentArea)

  selectRange(contentArea.firstChild as Node, 0, 5)
  fireEvent.select(contentArea)

  fireEvent.click(screen.getByTestId('toolbar-link'))

  return contentArea
}

// Applies a link to "hello", then places a collapsed caret inside that anchor
// and re-opens the popover — the "cursor inside an existing link" starting
// state for the prefill/replace and Escape-preserves-link cases.
export async function openLinkPopoverInsideExistingLink(href: string) {
  const contentArea = await applyLinkUrl(href)

  const anchor = contentArea.querySelector('a')
  if (!anchor) throw new Error('setup: expected an existing link on "hello"')
  selectRange(anchor.firstChild as Node, 2, 2)
  fireEvent.select(contentArea)

  fireEvent.click(screen.getByTestId('toolbar-link'))

  return contentArea
}

// Every shape pins the same three invariants and differs only in the expected
// href, so the href stays at the call site and the invariants live here.
//
// The absent alert is load-bearing rather than incidental: the defect is not
// only "no link" — it is that the visitor is actively told a genuinely fine
// address is bad. Pinning the absence of the rejection message is what
// distinguishes these from a silent no-op.
export function expectSoleLink(contentArea: HTMLElement, href: string) {
  const anchors = contentArea.querySelectorAll('a')
  expect(anchors).toHaveLength(1)
  expect(anchors[0].getAttribute('href')).toBe(href)
  // The link wraps the selection, not the whole text.
  expect(anchors[0].textContent).toBe('hello')
  // The rest of the document survives. Without this, normalization that
  // linked correctly but dropped the unselected " world" would pass every
  // caller — the anchor is right, so nothing else here would notice.
  expect(contentArea.textContent).toBe('hello world')
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
}

// The counterpart to expectSoleLink: the input was refused. Asserts NO anchor
// was produced AND the rejection message is shown — not a silent no-op. Both
// halves matter: a green that dropped the anchor but showed nothing would
// leave the visitor with a swallowed link and no signal, and a green that
// showed the alert but still linked would be a live dead/deceptive href. The
// alert presence is the ADR's whole reason for choosing the popover over
// window.prompt (a visible rejection signal), so pinning it here is on-contract.
export function expectRejected(contentArea: HTMLElement) {
  expect(contentArea.querySelectorAll('a')).toHaveLength(0)
  expect(screen.queryByRole('alert')).toBeInTheDocument()
}

// The empty/whitespace-apply outcome: the link mark is removed but the text it
// wrapped survives, the popover closes, and — unlike expectRejected — NO alert
// is shown. Clearing the field is a deliberate "remove the link", not a refused
// address, so the absent alert is what distinguishes this from a rejection.
export function expectLinkRemoved(contentArea: HTMLElement) {
  expect(contentArea.querySelectorAll('a')).toHaveLength(0)
  expect(contentArea.textContent).toBe('hello world')
  expect(screen.queryByTestId('link-popover')).not.toBeInTheDocument()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
}
