import type { Editor } from '@tiptap/react'

// The persisted form of the editor's content. ProseMirror keeps a trailing
// empty paragraph as the cursor's landing block after the last real block;
// serialized verbatim it would save a spurious empty <p> (and, via story 17's
// export, a blank block in the DOCX/PDF). Strip a single trailing empty
// paragraph so a document that ends on a real block persists exactly, and a
// genuinely empty document persists as empty content rather than <p></p>.
export function serializeEditorHtml(editor: Editor): string {
  return editor.getHTML().replace(/<p><\/p>$/, '')
}
