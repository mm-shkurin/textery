import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderEditorWithDocumentCreated, selectRange } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

// Renders a fresh editor, selects "hello" out of "hello world", opens the link
// popover, types `url` and presses Применить. Returns the content area so each
// test asserts on the resulting anchor. A helper rather than inline setup
// because the URL shapes below differ in exactly one value — the URL — and that
// difference is the whole point of the file.
//
// Deliberately local to this file rather than in ManualEditor.testSupport:
// ManualEditor.link.test.tsx drives the same popover but asserts *within* the
// flow (the popover is in the document, the full attribute set, aria-pressed
// toggling on cursor move), so it cannot be expressed as a call to this.
async function applyLinkUrl(url: string) {
  await renderEditorWithDocumentCreated()

  const contentArea = screen.getByTestId('editor-content-area')
  contentArea.textContent = 'hello world'
  fireEvent.input(contentArea)

  selectRange(contentArea.firstChild as Node, 0, 5)
  fireEvent.select(contentArea)

  fireEvent.click(screen.getByTestId('toolbar-link'))
  fireEvent.change(screen.getByTestId('link-url-input'), { target: { value: url } })
  fireEvent.click(screen.getByTestId('link-apply'))

  return contentArea
}

// Every shape below pins the same three invariants and differs only in the
// expected href, so the href stays at the call site and the invariants live
// here. Extracted from the assertion blocks, not from the setup: the varying
// input is still one literal per test, and each test keeps its own body so the
// reason it exists stays next to it.
//
// The absent alert is load-bearing rather than incidental: the defect is not
// only "no link" — it is that the visitor is actively told a genuinely fine
// address is bad. Pinning the absence of the rejection message is what
// distinguishes these from a silent no-op.
function expectSoleLink(contentArea: HTMLElement, href: string) {
  const anchors = contentArea.querySelectorAll('a')
  expect(anchors).toHaveLength(1)
  expect(anchors[0].getAttribute('href')).toBe(href)
  // The link wraps the selection, not the whole text.
  expect(anchors[0].textContent).toBe('hello')
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
}

describe('ManualEditor link URL shapes', () => {
  // RED (green-frontend-url-shapes owns the fix): normalizeHref's
  // HAS_SCHEME = /^[a-zA-Z][a-zA-Z0-9+.-]*:/ includes `.` in the class, so the
  // dotted HOST `example.com:` is indistinguishable from an RFC-3986 SCHEME.
  // The URL is passed through unnormalized, isAllowedUri rejects scheme
  // `example.com`, setLink returns false, and the visitor is told a genuinely
  // fine address is bad.
  it.skip('a host with a port and path is normalized to http:// rather than mistaken for a scheme', async () => {
    const contentArea = await applyLinkUrl('example.com:8080/path')

    expectSoleLink(contentArea, 'http://example.com:8080/path')
  })

  // RED, same root cause as above: `localhost:` matches HAS_SCHEME.
  // Kept separate from the dotted-host case because it is a distinct shape —
  // no dot at all, so a fix that merely requires "no `.` before the `:`" would
  // pass the test above and still break this one.
  it.skip('a dotless host with a port is normalized to http:// rather than mistaken for a scheme', async () => {
    const contentArea = await applyLinkUrl('localhost:3000')

    expectSoleLink(contentArea, 'http://localhost:3000')
  })

  // RED, same shape as `localhost:3000` and separate from it for the same
  // reason that case is separate from `example.com:8080` — one rung further
  // down. `localhost` is a well-known name, so it is the single most likely
  // string for green to special-case (`prefix === 'localhost'`) or to reach for
  // via a hostname allowlist. That green passes the test above and still breaks
  // every intranet host. The discriminator must be structural, not a name.
  it.skip('an arbitrary dotless host with a port is normalized to http://, not just the well-known localhost', async () => {
    const contentArea = await applyLinkUrl('myserver:8080')

    expectSoleLink(contentArea, 'http://myserver:8080')
  })

  // RED: a bare email has no `:` at all, so HAS_SCHEME correctly reports "no
  // scheme" — and normalizeHref then applies the WRONG default, producing
  // http://user@example.com (a http URL with a userinfo component). That
  // passes isAllowedUri, so it links successfully with no error: silently
  // wrong, which is worse than the rejection above. Disposition decided by the
  // user on 2026-07-16: mailto:, not a rejection and not the current http://.
  it.skip('a bare email address is normalized to a mailto: link, not an http:// userinfo URL', async () => {
    const contentArea = await applyLinkUrl('user@example.com')

    expectSoleLink(contentArea, 'mailto:user@example.com')
  })

  // RED, same shape as above and separate for the same reason: a single email
  // fixture is one data point, and the rule "an `@` with no scheme means
  // mailto:" is only shown to generalize by a second, structurally different
  // address — subdomain plus multi-label TLD, so the local part and the host
  // both differ from the case above.
  it.skip('a bare email on a subdomain with a multi-label TLD is also normalized to mailto:', async () => {
    const contentArea = await applyLinkUrl('admin@sub.example.co.uk')

    expectSoleLink(contentArea, 'mailto:admin@sub.example.co.uk')
  })

  // Regression guards, GREEN today and required to stay green: the fix to
  // HAS_SCHEME must not start prefixing http:// onto URLs that already carry a
  // real scheme. Not skipped — a red-phase file may carry passing regression
  // tests, and these have to be live to constrain green at all.
  it('an explicit https scheme passes through untouched', async () => {
    const contentArea = await applyLinkUrl('https://example.com/x')

    expectSoleLink(contentArea, 'https://example.com/x')
  })

  // The mailto case above makes this one load-bearing rather than incidental:
  // green must not "fix" emails by prefixing mailto: onto a string that already
  // has it, producing mailto:mailto:a@b.com.
  it('an explicit mailto scheme passes through untouched', async () => {
    const contentArea = await applyLinkUrl('mailto:a@b.com')

    expectSoleLink(contentArea, 'mailto:a@b.com')
  })
})
