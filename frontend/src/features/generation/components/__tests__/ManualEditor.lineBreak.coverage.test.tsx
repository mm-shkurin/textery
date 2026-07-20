import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

// Coverage backfill for scenario 3.3 (line-break-in-inline-doc-decision.md, approach A′).
// The original RED (ManualEditor.lineBreak.test.tsx) pinned only ONE save-payload shape and
// never exercised the KEYMAP path (hardBreakKeymap.ts) nor the load/parse path
// (hardBreakNode.ts parseHTML). These add the cases agent-review + premortem surfaced:
// a real keystroke inserting EXACTLY one <br> (guarding a double-insert), the stray trailing
// break being prevented, an intentional trailing break being kept, an interior break surviving,
// and a bare <br> in loaded content round-tripping without a parse error.
//
// The save payload asserted against is editor.getHTML(), captured as the 2nd arg the
// saveDocument mock receives (useDocumentSave.ts:84-85).

// Each test renders its own editor; without this the module-level saveDocument mock keeps
// calls from earlier tests and calls[0] / toHaveBeenCalledTimes(1) would read the wrong save.
beforeEach(() => {
  vi.clearAllMocks()
})

function sentPayload() {
  return vi.mocked(documentApi.saveDocument).mock.calls[0][1]
}

function countBreaks(html: string) {
  return (html.match(/<br\s*\/?>/g) ?? []).length
}

async function saveAndGetPayload() {
  vi.mocked(documentApi.saveDocument).mockResolvedValue({
    status: 'saved',
    version: 8,
    content: 'ignored',
  })
  fireEvent.click(screen.getByRole('button', { name: 'Сохранить' }))
  await waitFor(() => expect(documentApi.saveDocument).toHaveBeenCalledTimes(1))
  return sentPayload()
}

// Every editing test renders a created-document editor and then targets its content area.
async function renderAndGetContentArea() {
  await renderEditorWithDocumentCreated()
  return screen.getByTestId('editor-content-area')
}

describe('ManualEditor line break — keymap and parse coverage', () => {
  // Case 1: a real Enter keystroke drives the hardBreakKeymap (zero coverage before this).
  // ProseMirror binds its keymap plugin to the editable element's keydown; @testing-library's
  // fireEvent.keyDown dispatches a real KeyboardEvent that the plugin's handleKeyDown reads.
  it('a real Enter keystroke inserts exactly one <br>', async () => {
    const contentArea = await renderAndGetContentArea()

    fireEvent.keyDown(contentArea, { key: 'Enter' })

    const sent = await saveAndGetPayload()
    expect(countBreaks(sent)).toBe(1)
  })

  it('a Shift-Enter keystroke inserts exactly one <br>', async () => {
    const contentArea = await renderAndGetContentArea()

    fireEvent.keyDown(contentArea, { key: 'Enter', shiftKey: true })

    const sent = await saveAndGetPayload()
    expect(countBreaks(sent)).toBe(1)
  })

  // Case 2: typed non-empty content with NO trailing break — the ghost filler + cursor-helper
  // strip (hardBreakNode.ts) must keep the save payload free of any trailing <br> and of the
  // ProseMirror-trailingBreak helper class.
  it('typed content produces no stray trailing <br> in the save payload', async () => {
    const contentArea = await renderAndGetContentArea()
    contentArea.textContent = 'just one line'
    fireEvent.input(contentArea)

    const sent = await saveAndGetPayload()
    expect(/<br\s*\/?>\s*$/.test(sent)).toBe(false)
    expect(sent).not.toContain('ProseMirror-trailingBreak')
  })

  // Case 3: an INTENTIONAL trailing break is KEPT. Contrast with case 2: there the trailing
  // break would be an auto-injected filler / cursor helper and is stripped; here the user
  // pressed Enter after their text, so the resulting <br> at the end of content must survive
  // into the save payload. Driven through the real keymap (fireEvent.keyDown), which jsdom
  // dispatches to ProseMirror's keydown handler — the same path a browser keystroke takes.
  it('an intentional Enter at the end of typed content keeps the trailing <br>', async () => {
    const contentArea = await renderAndGetContentArea()
    contentArea.textContent = 'foo'
    fireEvent.input(contentArea)
    fireEvent.keyDown(contentArea, { key: 'Enter' })

    const sent = await saveAndGetPayload()
    expect(sent).toContain('foo<br>')
    expect(countBreaks(sent)).toBe(1)
  })

  // Case 4: an interior break is not over-stripped — only the stray TRAILING break dies.
  it('an interior <br> between two lines survives', async () => {
    const contentArea = await renderAndGetContentArea()
    contentArea.innerHTML = 'line one<br>line two'
    fireEvent.input(contentArea)

    const sent = await saveAndGetPayload()
    expect(sent).toContain('line one<br>line two')
    expect(countBreaks(sent)).toBe(1)
  })
})

describe('ManualEditor line break — load round-trip', () => {
  // Case 5: a saved document whose content ends in a bare <br> loads through the init/reopen
  // path (getDocument -> setContent). HardBreakNode's parseHTML `{ tag: 'br' }` rule plus the
  // marker attribute's `parseHTML: () => 'br'` supply the required attr, so no
  // "No value supplied for attribute marker" parse error, and the break is preserved.
  it('loading content ending in a bare <br> preserves the break with no parse error', async () => {
    vi.mocked(documentApi.createDocument).mockResolvedValue({
      documentId: 'doc-1',
      status: 'draft',
      version: 7,
    })
    vi.mocked(documentApi.getDocument).mockResolvedValue({
      documentId: 'doc-99',
      status: 'draft',
      content: 'kept line<br>next',
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
      expect(documentApi.getDocument).toHaveBeenCalledWith('doc-99')
    })

    const contentArea = await screen.findByTestId('editor-content-area')
    await waitFor(() => {
      expect(contentArea.innerHTML).toContain('kept line<br>next')
    })
    expect(countBreaks(contentArea.innerHTML)).toBe(1)
  })
})
