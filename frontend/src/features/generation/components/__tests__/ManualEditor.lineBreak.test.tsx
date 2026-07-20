import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import { renderEditorWithDocumentCreated } from './ManualEditor.testSupport'

vi.mock('../../api/documentApi')

// Bug (Story 05, scenario 3.3): in Ручной режим the text prints on a single line
// only — pressing Enter cannot make a line break. Root cause: the editor's Document
// holds `inline*` content (no paragraph wrapper), and StarterKit's hardBreak is
// disabled, so no schema node can represent a line break; a `<br>` that reaches the
// document is dropped by ProseMirror's schema-driven reconciliation, collapsing the
// two lines into one.
//
// ADR (line-break-in-inline-doc-decision.md, approach A′): re-enable hardBreak so a
// break has a schema node, and strip the stray trailing hardBreak that the domObserver
// reparses from ProseMirror's cursor helper. This test pins the SAVE-payload contract,
// asserting against editor.getHTML() (captured via the saveDocument mock — the exact
// value performSave sends, useDocumentSave.ts:84), which is what actually persists and
// is what the trailing-break strip must clean:
//   1. A break BETWEEN two lines survives: `line one<br>line two` round-trips exactly —
//      one <br>, both lines intact.
//   2. No stray trailing <br>: the persisted payload must not end in a <br>.
// TDD Red Phase - hardBreak disabled: schema reconciliation drops the <br>, so the
// save payload is 'line one line two' (break collapsed to a space) instead of
// 'line one<br>line two'. Un-skip in GREEN once approach A′ (re-enable hardBreak +
// strip trailing break) is implemented.
describe('ManualEditor line break', () => {
  it('persists a hard line break between two lines with no stray trailing break', async () => {
    await renderEditorWithDocumentCreated()

    const contentArea = screen.getByTestId('editor-content-area')
    contentArea.innerHTML = 'line one<br>line two'
    fireEvent.input(contentArea)

    vi.mocked(documentApi.saveDocument).mockResolvedValue({
      status: 'saved',
      version: 8,
      content: 'line one<br>line two',
    })

    fireEvent.click(screen.getByRole('button', { name: 'Сохранить' }))

    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    const sent = vi.mocked(documentApi.saveDocument).mock.calls[0][1]
    expect(sent).toBe('line one<br>line two')
    expect((sent.match(/<br\s*\/?>/g) ?? []).length).toBe(1)
    expect(/<br\s*\/?>\s*$/.test(sent)).toBe(false)
  })
})
