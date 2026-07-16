import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderEditorWithDocumentCreated, selectRange } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

describe('ManualEditor link toolbar', () => {
  it('applying a URL from the link popover turns the selected text into a hyperlink and marks the link button active', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.textContent = 'hello world'
    fireEvent.input(contentArea)

    const textNode = contentArea.firstChild as Node
    selectRange(textNode, 0, 5)
    fireEvent.select(contentArea)

    const linkButton = screen.getByTestId('toolbar-link')
    fireEvent.click(linkButton)

    expect(screen.getByTestId('link-popover')).toBeInTheDocument()
    fireEvent.change(screen.getByTestId('link-url-input'), {
      target: { value: 'https://example.com' },
    })
    fireEvent.click(screen.getByTestId('link-apply'))

    // Asserted as parsed fields rather than a raw innerHTML string: Link's
    // renderHTML does mergeAttributes(options.HTMLAttributes, markAttrs), so
    // the attribute *order* in the serialized <a> is an implementation detail
    // of mergeAttributes. Order is the only thing given up — every attribute
    // innerHTML would have pinned is pinned below, by name.
    const anchors = contentArea.querySelectorAll('a')
    expect(anchors).toHaveLength(1)
    const anchor = anchors[0]

    // The exact attribute set: no more, no less. This is what the innerHTML
    // precedent bought for free — without it, a stray attribute (a `class`, a
    // `title`, a rogue `data-*`) lands unnoticed.
    expect([...anchor.getAttributeNames()].sort()).toEqual(['href', 'rel', 'target'])
    expect(anchor.getAttribute('href')).toBe('https://example.com')
    // target/rel are not incidental defaults to shrug at: with no exit guard on
    // this page (ADR § "Knowingly unverified"), a same-tab navigation out of the
    // editor is total content loss, and rel is what keeps the opened tab from
    // reaching back through window.opener. They are Link's defaults today
    // (extension-link addAttributes: target/rel default from options.
    // HTMLAttributes = '_blank' / 'noopener noreferrer nofollow'); pinning them
    // is what makes a silent change to those defaults fail here rather than in
    // production.
    expect(anchor.getAttribute('target')).toBe('_blank')
    expect(anchor.getAttribute('rel')).toBe('noopener noreferrer nofollow')

    expect(anchor.textContent).toBe('hello')
    expect(contentArea.textContent).toBe('hello world')
    expect(linkButton).toHaveAttribute('aria-pressed', 'true')

    // The Gherkin says the button is active *while the cursor is within a
    // link* — the assertion above alone is satisfied by a hardcoded
    // `isActive: () => true`. Moving the cursor out is what gives the clause
    // teeth, mirroring the bold/strike/underline deactivation tests.
    const trailingTextNode = contentArea.lastChild as Node
    selectRange(trailingTextNode, 3, 3)
    fireEvent.select(contentArea)

    expect(linkButton).toHaveAttribute('aria-pressed', 'false')
  })
})
