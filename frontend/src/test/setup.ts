import '@testing-library/jest-dom'

// jsdom implements no layout, so it lacks the geometry APIs ProseMirror's
// mousedown handler walks (posAtCoords -> posFromElement -> findOffsetInNode).
// Any test that dispatches a real pointer event onto the editor DOM otherwise
// throws an unhandled TypeError deep inside prosemirror-view. Empty rects and a
// null hit-test are the documented "no geometry here" contract, which
// ProseMirror handles gracefully.
if (typeof document.elementFromPoint !== 'function') {
  document.elementFromPoint = () => null
}
const emptyRect = () => ({
  x: 0,
  y: 0,
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  width: 0,
  height: 0,
  toJSON: () => ({}),
})
if (typeof Range.prototype.getClientRects !== 'function') {
  Range.prototype.getClientRects = () => Object.assign([], { item: () => null })
  Range.prototype.getBoundingClientRect = emptyRect as never
}
