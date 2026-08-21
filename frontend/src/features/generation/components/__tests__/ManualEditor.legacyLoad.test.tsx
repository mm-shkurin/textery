import { describe, expect, it, vi } from 'vitest'
import { waitFor } from '@testing-library/react'
import { renderEditorReopeningDocument } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

// Scenario E1.2 / ADR back-compat contract: a document saved BEFORE the block-schema
// migration (inline-only schema, formatting as top-level marks) must load in the upgraded
// block editor with NO TEXT DROPPED. This is a characterization guard, not a red→green
// cycle — the E1.1 migration already delivers the contract; ProseMirror's DOMParser lifts
// the retired marks' wrapper elements into block nodes. These tests pin that behaviour so a
// future extension/parse-rule change cannot silently reintroduce the data loss the premortem
// flagged (centered-<div> child-lift). Alignment loss on a legacy <div> is ADR-defined-lossy
// ("mark → node, lossy-but-defined; no text is dropped"), so it is asserted as the documented
// outcome — text survives, the center alignment does not.

describe('ManualEditor legacy inline-only load (E1.2 back-compat guard)', () => {
  it('bare inline text with an old <br> line break wraps into one paragraph, all text intact', async () => {
    const contentArea = await renderEditorReopeningDocument('First line<br>second line')
    await waitFor(() => {
      expect(contentArea.innerHTML).toBe('<p>First line<br>second line</p>')
    })
  })

  it('a legacy centered <div> preserves its text; alignment is ADR-defined-lossy (plain paragraph)', async () => {
    const contentArea = await renderEditorReopeningDocument(
      '<div style="text-align: center">Centered legacy text</div>',
    )
    await waitFor(() => {
      // Text survives; the <div>-mark alignment does not (TextAlign parses text-align off
      // heading/paragraph only, never a <div>) — the documented lossy-but-defined outcome.
      expect(contentArea.innerHTML).toBe('<p>Centered legacy text</p>')
    })
  })

  it('text interleaved with a centered <div> child-lifts into paragraphs without dropping any run', async () => {
    const contentArea = await renderEditorReopeningDocument(
      'Leading text<div style="text-align:center">Centered</div>Trailing text',
    )
    await waitFor(() => {
      // The premortem feared child-lifting would drop the surrounding text; it does not —
      // every run becomes its own paragraph, none lost.
      expect(contentArea.innerHTML).toBe('<p>Leading text</p><p>Centered</p><p>Trailing text</p>')
    })
  })

  it('legacy mark HTML (<h3>, <blockquote>) parses to heading/blockquote nodes with text intact', async () => {
    const contentArea = await renderEditorReopeningDocument(
      '<h3>Legacy heading</h3><blockquote>Legacy quote</blockquote>',
    )
    await waitFor(() => {
      const heading = contentArea.querySelector('h3')
      const quote = contentArea.querySelector('blockquote')
      // Mark → node conversion: the retired Heading3Mark/BlockquoteMark HTML lands on the
      // StarterKit heading/blockquote NODES, not stripped to bare text.
      expect(heading?.textContent).toBe('Legacy heading')
      expect(quote?.textContent).toBe('Legacy quote')
    })
  })

  it('a combined legacy document loses no text across every retired-mark form', async () => {
    const contentArea = await renderEditorReopeningDocument(
      'Intro<br>line<div style="text-align:center">Centred</div>' +
        '<h3>Heading</h3><blockquote>Quoted</blockquote>Outro',
    )
    await waitFor(() => {
      expect(contentArea.querySelector('h3')).toBeInstanceOf(HTMLHeadingElement)
    })
    // Whole-document no-data-loss, pinned to exact structure: every authored run survives
    // in order, each retired-mark form lands on its node, and the legacy centered <div>
    // still collapses to a plain <p> (alignment is ADR-defined-lossy, text is not).
    expect(contentArea.innerHTML).toBe(
      '<p>Intro<br>line</p><p>Centred</p><h3>Heading</h3>' +
        '<blockquote><p>Quoted</p></blockquote><p>Outro</p>',
    )
  })
})
