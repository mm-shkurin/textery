import { afterEach, describe, expect, it, vi } from 'vitest'
import type { EditorView } from '@tiptap/pm/view'
import { flushDomObserverOnInput, syncNativeSelectionToProseMirror } from '../editorDomSync'

// The guards in editorDomSync, each of which exists because something reaches these two functions
// that ProseMirror will not survive being handed.
//
// They are exercised through ManualEditor only on their HAPPY paths — a normal keystroke, a normal
// selection. Every guard below is the abnormal one, and none of them can be produced by typing:
// an IME composition, a stubbed-out domObserver, a selection anchored outside the editor, a
// posAtDOM that returns -1 or throws. Driven against a hand-built view for that reason, and
// because a fake makes it possible to assert the thing that actually matters — that the editor's
// state was NOT touched.
//
// Both functions return false unconditionally: that is the ProseMirror handler contract ("I did
// not handle this event, carry on"), not a result. So every assertion here is about what was
// called, never about the return value, which would pass on any implementation at all.

function fakeView(overrides: Record<string, unknown> = {}): EditorView {
  const dom = document.createElement('div')
  document.body.appendChild(dom)
  return {
    dom,
    dispatch: vi.fn(),
    posAtDOM: vi.fn(() => 1),
    state: { doc: {}, tr: { setSelection: vi.fn() } },
    ...overrides,
  } as unknown as EditorView
}

// A native Selection is not constructible, and jsdom's real one cannot be made to anchor at a node
// outside the editor while still reporting rangeCount — so the whole object is stubbed at the
// window seam the function reads it from.
function stubSelection(view: EditorView, selection: unknown) {
  vi.spyOn(view.dom.ownerDocument.defaultView as Window, 'getSelection').mockReturnValue(
    selection as Selection,
  )
}

afterEach(() => {
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('flushDomObserverOnInput', () => {
  it('does not flush mid-composition', () => {
    const flush = vi.fn()
    const view = fakeView({ domObserver: { flush } })

    flushDomObserverOnInput(view, new InputEvent('beforeinput', { isComposing: true }))

    // ProseMirror defers DOM reconciliation while a composition is open because composed text -
    // CJK, Russian dead-key sequences - mutates the DOM incrementally before compositionend.
    // Flushing here commits a partial, garbled composition into the document model, and the user
    // sees their half-typed syllable frozen into the document.
    expect(flush).not.toHaveBeenCalled()
  })

  it('flushes an ordinary input event', () => {
    const flush = vi.fn()
    const view = fakeView({ domObserver: { flush } })

    flushDomObserverOnInput(view, new InputEvent('beforeinput', { isComposing: false }))

    expect(flush).toHaveBeenCalledTimes(1)
  })

  it('does nothing when the view exposes no domObserver to flush', () => {
    // `domObserver` is EditorView internals, not public API: a prosemirror-view upgrade may rename
    // or drop it, and the failure mode without this guard is a TypeError thrown from a beforeinput
    // handler - i.e. the editor breaking on the first keystroke, on someone else's release.
    expect(() => flushDomObserverOnInput(fakeView(), new InputEvent('beforeinput'))).not.toThrow()
  })
})

describe('syncNativeSelectionToProseMirror', () => {
  it('leaves the editor alone when there is no selection at all', () => {
    const view = fakeView()
    stubSelection(view, null)

    syncNativeSelectionToProseMirror(view)

    expect(view.dispatch).not.toHaveBeenCalled()
  })

  it('leaves the editor alone when the selection holds no range', () => {
    const view = fakeView()
    stubSelection(view, { rangeCount: 0 })

    syncNativeSelectionToProseMirror(view)

    expect(view.dispatch).not.toHaveBeenCalled()
  })

  it('leaves the editor alone when an endpoint node is null', () => {
    const view = fakeView()
    stubSelection(view, { rangeCount: 1, anchorNode: null, focusNode: view.dom })

    syncNativeSelectionToProseMirror(view)

    expect(view.dispatch).not.toHaveBeenCalled()
  })

  it('ignores a selection anchored outside the editor', () => {
    const view = fakeView()
    const outside = document.createElement('p')
    document.body.appendChild(outside)
    stubSelection(view, {
      rangeCount: 1,
      anchorNode: outside,
      anchorOffset: 0,
      focusNode: outside,
      focusOffset: 0,
    })

    syncNativeSelectionToProseMirror(view)

    // Selecting the page heading, or text in a sibling panel, must not move the caret inside a
    // document the user was not selecting - and posAtDOM on a foreign node is undefined behaviour,
    // not a caught error.
    expect(view.posAtDOM).not.toHaveBeenCalled()
    expect(view.dispatch).not.toHaveBeenCalled()
  })

  it('ignores a position that does not map into the document', () => {
    const inside = document.createElement('span')
    const view = fakeView({ posAtDOM: vi.fn(() => -1) })
    view.dom.appendChild(inside)
    stubSelection(view, {
      rangeCount: 1,
      anchorNode: inside,
      anchorOffset: 0,
      focusNode: inside,
      focusOffset: 0,
    })

    syncNativeSelectionToProseMirror(view)

    expect(view.dispatch).not.toHaveBeenCalled()
  })

  it('survives posAtDOM throwing instead of crashing the editor', () => {
    const inside = document.createElement('span')
    const view = fakeView({
      posAtDOM: vi.fn(() => {
        throw new RangeError('Position outside of fragment')
      }),
    })
    view.dom.appendChild(inside)
    stubSelection(view, {
      rangeCount: 1,
      anchorNode: inside,
      anchorOffset: 0,
      focusNode: inside,
      focusOffset: 0,
    })

    // A triple-click spanning a block boundary is the ordinary way to reach this. The handler runs
    // off a native `select` event, so an uncaught throw here is not a failed selection sync - it
    // unmounts the editor subtree into the ErrorBoundary, with whatever the user typed still only
    // in the DOM.
    expect(() => syncNativeSelectionToProseMirror(view)).not.toThrow()
    expect(view.dispatch).not.toHaveBeenCalled()
  })
})
