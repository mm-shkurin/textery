import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { openLinkPopover } from './ManualEditor.link.testSupport'

vi.mock('../../api/documentApi')

// Characterization (2026-07-22, red-frontend-coverage-click-inside, Story 5 / 7.9):
// pins LinkPopover.tsx:99-104 — the click-outside mousedown handler's three
// "inside" exclusions (popover / toolbar / editor content). A mousedown whose
// target is inside any of them must take the early return and NOT reach apply():
// the popover stays open and no link is created. That true-branch is a coverage
// gap no other test takes (it is also premortem CREDIBLE-2 from commit dee4260 —
// wrong-target apply). The behaviour is already implemented, so these stay LIVE.
//
// A valid href is typed first so that if the guard failed and apply() DID run, it
// would wrap the captured "hello" selection in an anchor — the length-0 anchor
// assertion is what proves the mousedown was excluded rather than silently no-op.
describe('ManualEditor link popover — mousedown inside the editor UI does not apply', () => {
  // Three exclusion targets, one shared body. Two rows independently kill their
  // mutant: the editor-content row is caught ONLY by editorDom.contains (line 102),
  // the toolbar-bold button ONLY by toolbar.contains (line 101 — the bold button
  // renders bare in .me-toolbar, outside the popover span). The popover-input row,
  // however, does NOT independently exercise popover.contains (line 100): the
  // popover renders INSIDE .me-toolbar (ManualEditorToolbar wraps it in
  // .me-link-popover-anchor), so link-url-input is contained by BOTH the popover
  // (100) and the toolbar (101). Deleting line 100 alone leaves line 101 catching
  // the input, so that mutant survives via this DOM path — line 100 is defensive/
  // redundant given the current nesting. The row is kept because it still pins the
  // observable contract (a mousedown on the input keeps the popover open, applies
  // no link); making line 100 independently testable would require relocating the
  // popover out of .me-toolbar, a production change outside this test's scope.
  // Same three invariants hold for all — popover still mounted, no anchor,
  // text intact — so the rows share one body and differ only in the target.
  it.each([
    ['the editor content DOM (caret reposition)', () => screen.getByTestId('editor-content-area')],
    ['a sibling toolbar button', () => screen.getByTestId('toolbar-bold')],
    ['the popover input itself', () => screen.getByTestId('link-url-input')],
  ])('mousedown on %s keeps the popover open and applies no link', async (_label, getTarget) => {
    const contentArea = await openLinkPopover()

    fireEvent.change(screen.getByTestId('link-url-input'), {
      target: { value: 'https://example.com' },
    })

    fireEvent.mouseDown(getTarget())

    expect(screen.queryByTestId('link-popover')).toBeInTheDocument()
    expect(contentArea.querySelectorAll('a')).toHaveLength(0)
    expect(contentArea.textContent).toBe('hello world')
  })
})
