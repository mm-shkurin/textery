import { TextSelection } from '@tiptap/pm/state'
import type { EditorView } from '@tiptap/pm/view'

// `domObserver` is EditorView's internal MutationObserver-based DOM
// reconciler. It isn't part of the public prosemirror-view type
// definitions, but it's a real runtime property we need to force-flush
// synchronously (see `flushDomObserverOnInput` below).
function asEditorViewWithDomObserver(
  view: EditorView,
): EditorView & { domObserver: { flush: () => void } } {
  return view as EditorView & { domObserver: { flush: () => void } }
}

// ProseMirror normally intercepts real keystrokes via beforeinput/keydown
// before the DOM mutates, so it doesn't need this in the browser. Its
// MutationObserver-based fallback (domObserver) reconciles any DOM edits it
// didn't catch that way (e.g. spellcheck, or - in this test environment -
// programmatic textContent writes) by diffing the real DOM against its
// document model, so existing marks are preserved. That reconciliation
// normally runs on a microtask; forcing it synchronously here just makes it
// run before the next assertion instead of after, it does not change what
// transaction gets produced.
//
// Guarded against IME composition: ProseMirror deliberately defers DOM
// reconciliation while `event.isComposing` is true, because composed text
// (CJK, Kazakh/Russian dead-key sequences, etc.) mutates the DOM
// incrementally before compositionend. Flushing mid-composition would
// commit a partial, garbled composition into the document model.
export function flushDomObserverOnInput(view: EditorView, event: Event): boolean {
  if (event instanceof InputEvent && event.isComposing) return false
  const withDomObserver = asEditorViewWithDomObserver(view)
  if (typeof withDomObserver.domObserver?.flush !== 'function') return false
  withDomObserver.domObserver.flush()
  return false
}

// Keep the editor's document selection in sync with the browser's native
// Selection object, so toolbar commands (e.g. bold) act on whatever text the
// user has actually highlighted in the DOM.
//
// `posAtDOM` can return an invalid position (or `TextSelection.create` can
// throw) for selections that don't map cleanly onto an inline text range --
// e.g. a triple-click spanning a block boundary, or a selection landing on
// a non-content DOM node. Swallow those rather than letting an uncaught
// exception from a native `select` event crash the whole editor.
export function syncNativeSelectionToProseMirror(view: EditorView): boolean {
  const domSelection = view.dom.ownerDocument.defaultView?.getSelection()
  if (!domSelection || domSelection.rangeCount === 0) return false
  const { anchorNode, anchorOffset, focusNode, focusOffset } = domSelection
  if (!anchorNode || !focusNode) return false
  if (!view.dom.contains(anchorNode) || !view.dom.contains(focusNode)) return false
  try {
    const anchorPos = view.posAtDOM(anchorNode, anchorOffset)
    const headPos = view.posAtDOM(focusNode, focusOffset)
    if (anchorPos < 0 || headPos < 0) return false
    const selection = TextSelection.create(view.state.doc, anchorPos, headPos)
    view.dispatch(view.state.tr.setSelection(selection))
  } catch {
    // Selection didn't map onto a valid inline range -- leave ProseMirror's
    // existing selection untouched rather than crashing the editor.
  }
  return false
}
