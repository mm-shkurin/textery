import { useEffect, useRef } from 'react'
import type { Editor } from '@tiptap/react'

// Puts the text of a COMPLETED GENERATION into the editor ONCE, the first render at which the
// editor instance exists (story 18, scenario 2.1). A no-op on every other path — the history-open
// and manual paths pass no content and this hook never touches their editor.
//
// Both halves of that sentence are load-bearing, and each is why this is not simpler code:
//
//   - not a render-time `setContent`: `editor` is null on the first render (Tiptap builds the
//     instance in an effect of its own), so there is nothing to write to yet. The effect re-runs
//     when the instance arrives, which is the earliest moment the seed can happen.
//   - not `[]` deps, and not re-runnable: the ref is what makes it once-only. Seeding again on a
//     later run would replace whatever the user has typed with the original generation — the
//     "it deleted my report" failure, arriving silently mid-edit.
//
// The ref rather than a `documentId`/`hasSeeded` state: it must not cause a render, and it must
// survive StrictMode's double-invocation, which is exactly the window it exists to cover.
export function useSeedGeneratedContent(editor: Editor | null, generatedContent?: string): void {
  const seededRef = useRef(false)

  useEffect(() => {
    if (seededRef.current || generatedContent === undefined || !editor) return
    seededRef.current = true
    editor.commands.setContent(generatedContent)
  }, [editor, generatedContent])
}
