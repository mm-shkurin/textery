import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'

vi.mock('../../api/documentApi')

// Scenario 1.1 (07_Editor_Extension_Tests): multi-paragraph block content —
// paragraphs, H1, H2, H3 — must round-trip through the editor's HTML
// serialization as the correct semantic BLOCK elements, not as inline text or
// marks. This is the root blocker the block-schema migration (ADR 2026-07-26)
// resolves: Document is `block+`, so paragraphs and headings are real nodes.
//
// The round-trip contract is the SAVED form (serializeEditorHtml → the 2nd arg
// saveDocument receives): the content the editor loaded is re-serialized to the
// exact same semantic HTML it would persist, with the trailing empty paragraph
// ProseMirror keeps as a cursor-landing block stripped away.
describe('ManualEditor block-schema round-trip', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  async function loadAndSave(content: string): Promise<string> {
    vi.mocked(documentApi.createDocument).mockResolvedValue({
      documentId: 'doc-1',
      status: 'draft',
      version: 7,
    })
    vi.mocked(documentApi.getDocument).mockResolvedValue({
      documentId: 'doc-99',
      status: 'draft',
      content,
      version: 3,
    })
    vi.mocked(documentApi.saveDocument).mockResolvedValue({
      status: 'saved',
      version: 4,
      content,
    })

    render(
      <ManualEditor
        documentType="doklad"
        documentTypeLabel="Доклад"
        onBack={vi.fn()}
        existingDocumentId="doc-99"
      />,
    )

    await waitFor(() => {
      expect(documentApi.getDocument).toHaveBeenCalledExactlyOnceWith(
        'doc-99',
        expect.any(AbortSignal),
      )
    })
    // Let setContent apply the loaded document before saving.
    await screen.findByTestId('editor-content-area')
    await waitFor(() => {
      expect(
        screen.getByTestId('editor-content-area').querySelectorAll('p, h1, h2, h3').length,
      ).toBeGreaterThan(0)
    })

    fireEvent.click(screen.getByRole('button', { name: 'Сохранить' }))
    await waitFor(() => {
      expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    })
    return vi.mocked(documentApi.saveDocument).mock.calls[0][1]
  }

  it('paragraphs, H1, H2, and H3 reload and re-serialize as their correct semantic block elements', async () => {
    const blockContent =
      '<p>First paragraph.</p>' +
      '<p>Second paragraph.</p>' +
      '<h1>Main Title</h1>' +
      '<h2>Section Heading</h2>' +
      '<h3>Subsection Heading</h3>'

    const sent = await loadAndSave(blockContent)

    // Exact round-trip: the two paragraphs stay <p>, the three headings stay
    // <h1>/<h2>/<h3> (real nodes, not inline text or marks), and the trailing
    // empty paragraph ProseMirror renders after the final heading is stripped.
    expect(sent).toBe(blockContent)

    // The rendered DOM carries the semantic block elements the user sees.
    const contentArea = screen.getByTestId('editor-content-area')
    expect(contentArea.querySelectorAll('h1')).toHaveLength(1)
    expect(contentArea.querySelectorAll('h2')).toHaveLength(1)
    expect(contentArea.querySelectorAll('h3')).toHaveLength(1)
  })

  // Premortem #2: inline marks (bold, italic, code, link) and a block alignment
  // attribute must survive co-resident with block nodes through a save→reload,
  // not just bare-text blocks. A heading, a paragraph mixing four inline marks,
  // and a centered paragraph round-trip to the exact same serialized HTML (link
  // gains its target/rel defaults on render; alignment is a paragraph style).
  it('inline marks and alignment survive co-resident with block nodes through a round-trip', async () => {
    const mixedContent =
      '<h1>Title</h1>' +
      '<p><strong>bold</strong> plain <em>italic</em> <code>snippet</code> ' +
      '<a href="https://example.com">link</a></p>' +
      '<p style="text-align: center">centered</p>'

    const sent = await loadAndSave(mixedContent)

    expect(sent).toBe(
      '<h1>Title</h1>' +
        '<p><strong>bold</strong> plain <em>italic</em> <code>snippet</code> ' +
        '<a target="_blank" rel="noopener noreferrer nofollow" href="https://example.com">link</a></p>' +
        '<p style="text-align: center;">centered</p>',
    )
  })
})
