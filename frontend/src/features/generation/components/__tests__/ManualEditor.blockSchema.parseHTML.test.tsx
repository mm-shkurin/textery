import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'

vi.mock('../../api/documentApi')

// Scenario 1.1 (07_Editor_Extension_Tests): multi-paragraph block content —
// paragraphs, H1, H2, H3 — must round-trip through the editor's HTML
// serialization as the correct semantic BLOCK elements, not as inline text or
// marks. This is the root blocker: the doc schema is `inline*` today, so block
// nodes are unreachable and this content collapses on parse.
describe('ManualEditor block-schema round-trip', () => {
  // RED (skipped until block-schema green): the `inline*` doc schema strips
  // <p>/<h1>/<h2> block tags — they collapse to bare inline text — and only the
  // Heading3Mark keeps <h3>. Actual innerHTML:
  // "First paragraph.Second paragraph.Main TitleSection Heading<h3>Subsection Heading</h3>".
  it.skip('paragraphs, H1, H2, and H3 reload as their correct semantic block elements', async () => {
    const blockContent =
      '<p>First paragraph.</p>' +
      '<p>Second paragraph.</p>' +
      '<h1>Main Title</h1>' +
      '<h2>Section Heading</h2>' +
      '<h3>Subsection Heading</h3>'

    vi.mocked(documentApi.createDocument).mockResolvedValue({
      documentId: 'doc-1',
      status: 'draft',
      version: 7,
    })
    vi.mocked(documentApi.getDocument).mockResolvedValue({
      documentId: 'doc-99',
      status: 'draft',
      content: blockContent,
      version: 3,
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
      expect(documentApi.getDocument).toHaveBeenCalledExactlyOnceWith('doc-99')
    })

    const contentArea = await screen.findByTestId('editor-content-area')
    await waitFor(() => {
      expect(contentArea.innerHTML).toBe(blockContent)
    })
  })
})
