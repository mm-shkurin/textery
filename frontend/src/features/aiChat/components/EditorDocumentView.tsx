import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'

interface EditorDocumentViewProps {
  content: string
}

// The editor root for `/documents/:documentId`. It carries the SAME `manual-editor` testid as the
// Story 5/18 editor because it is the same thing to the user — the two are sibling routes and
// never mount together, so no test can see both at once.
//
// The document's HTML goes through Tiptap's schema rather than `dangerouslySetInnerHTML`:
// anything the schema does not know is dropped, which keeps stored markup from becoming a script
// injection point.
//
// `immediatelyRender` so the content is in the FIRST commit: this route resolves its document
// before mounting this view, and deferring the render would put the text one tick behind the
// element that contains it.
export function EditorDocumentView({ content }: EditorDocumentViewProps) {
  const editor = useEditor({
    extensions: [StarterKit],
    content,
    editable: false,
    immediatelyRender: true,
  })

  return (
    <div className="ac-editor" data-testid="manual-editor">
      <EditorContent editor={editor} />
    </div>
  )
}
