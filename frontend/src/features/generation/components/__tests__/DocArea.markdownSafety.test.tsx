import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DocArea } from '../DocArea'

// The generated document is the one string in this app that is BOTH server-supplied and
// user-influenced: the model writes it, and the user writes the topic the model is answering.
// DocArea hands it to <ReactMarkdown> raw.
//
// Nothing pinned that seam. The editor's href path carries four files of guards
// (ManualEditor.link.urlShapes.*) against exactly this hazard class, while the render path — the
// one fed by an LLM rather than by the user's own typing — had none. The asymmetry is the bug
// this file closes: adding `rehype-raw` for richer output, or swapping in a renderer with a
// different urlTransform default, turns a stored XSS into a session handover (tokens live in
// sessionStorage, which any script on the origin reads) and no test today would go red.
//
// These assert react-markdown's DEFAULTS, deliberately. A default nobody pins is a default
// somebody removes.
const COMPLETED = {
  state: 'completed' as const,
  volumePages: 3,
  error: null,
  documentType: 'doklad' as const,
  label: 'Доклад',
  createdAt: '2026-07-29T10:00:00Z',
  onReset: () => {},
}

describe('DocArea — what the generated markdown is not allowed to become', () => {
  it('renders embedded HTML as text rather than as markup', () => {
    render(<DocArea {...COMPLETED} content={'Введение\n\n<img src=x onerror="alert(1)">\n'} />)

    const body = screen.getByTestId('doc-body')
    // No element, and the source is visible as prose. Asserting the absence of <img> alone would
    // pass on a renderer that dropped the tag silently; the textContent half proves it was
    // escaped rather than swallowed, which is what keeps the document faithful too.
    expect(body.querySelector('img')).toBeNull()
    expect(body).toHaveTextContent('<img src=x onerror="alert(1)">')
  })

  it('refuses a javascript: link a markdown link syntax asks for', () => {
    render(<DocArea {...COMPLETED} content={'[кликни](javascript:alert(document.cookie))'} />)

    const link = screen.getByTestId('doc-body').querySelector('a')
    // The anchor still renders — the text is part of the document — but its href must not be a
    // live javascript: URL. react-markdown's default urlTransform rewrites it to an empty href;
    // pinned by what it must NOT start with, so a future transform that neutralizes it a
    // different way (about:blank, dropping the attribute) also passes, and only a live one fails.
    expect(link).toBeInstanceOf(HTMLAnchorElement)
    expect(link?.getAttribute('href') ?? '').not.toMatch(/^javascript:/i)
  })

  it('keeps an ordinary https link live', () => {
    render(<DocArea {...COMPLETED} content={'[источник](https://example.com/a)'} />)

    // The negative pins above are satisfied by a renderer that breaks every link. This is what
    // stops the guard from being over-tightened into a regression of its own.
    expect(screen.getByTestId('doc-body').querySelector('a')).toHaveAttribute(
      'href',
      'https://example.com/a',
    )
  })
})
