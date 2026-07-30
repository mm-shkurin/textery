import { useEffect, useRef } from 'react'
import type { Editor } from '@tiptap/react'
import { createDocumentFromGeneration } from '../api/documentApi'
import { describeFailure } from '../../../shared/api/send'

export const CONVERT_FAILED_MESSAGE =
  'Не удалось открыть сгенерированный документ. Проверьте соединение и обновите страницу — до этого сохранение недоступно.'

// The auto path's init (story 18, scenarios 2.1–2.3), split from useDocumentInit because it is a
// different operation with a different failure mode: the manual paths GET or POST a document, this
// one converts a generation into one. Folding it into the same effect would put three mutually
// exclusive branches behind one `if` chain and give the conversion the manual path's error copy.
//
// What it does, in the order it matters:
//
//   1. Seeds the editor with the generation's own text IMMEDIATELY. The user watched this text
//      being written; an editor that mounts blank while a round trip completes reads as "it
//      deleted my report". Unformatted for that instant — markdown syntax is still visible — which
//      is the price of not showing an empty page.
//   2. Converts the generation into a Document, and adopts the SERVER's HTML. This is what turns
//      `## Введение` from a literal line of text into a heading, and it is also what produces the
//      documentId and version without which the editor cannot save or export at all.
//
// The response is the source of the content, never a follow-up GET (scenario 2.3): a re-read on a
// multi-instance backend can land on an instance that has not yet seen the insert, and the editor
// would open empty on text that is already stored.
export function useGeneratedDocumentInit({
  generationId,
  generatedContent,
  editor,
  setDocumentId,
  setVersion,
  onError,
}: {
  generationId?: string
  generatedContent?: string
  editor: Editor | null
  setDocumentId: (id: string) => void
  setVersion: (version: number) => void
  onError: (message: string | null) => void
}): void {
  // One key for the life of this editor, minted once. Load-bearing under StrictMode (main.tsx),
  // which double-invokes effects in dev: `cancelled` suppresses the second run's setState but NOT
  // its request, so the POST genuinely fires twice. One key makes those a request and its replay,
  // which the endpoint answers with the same document instead of a second one.
  const idempotencyKeyRef = useRef<string>('')
  if (!idempotencyKeyRef.current) {
    idempotencyKeyRef.current = crypto.randomUUID()
  }
  // Seed once, ever. Re-seeding on a later effect run would replace whatever the user has typed
  // with the original generation — silent mid-edit data loss, arriving as "it deleted my report".
  const seededRef = useRef(false)
  const convertedRef = useRef(false)

  useEffect(() => {
    if (generationId === undefined || generatedContent === undefined || !editor) return
    if (!seededRef.current) {
      seededRef.current = true
      editor.commands.setContent(generatedContent)
    }
    if (convertedRef.current) return
    convertedRef.current = true

    let cancelled = false
    createDocumentFromGeneration(generationId, idempotencyKeyRef.current)
      .then((result) => {
        if (cancelled) return
        setDocumentId(result.documentId)
        // The server's version, not a guess: `useState(1)` would ship a stale token on the first
        // save and collect a 409 blaming a concurrent save that never happened.
        setVersion(result.version)
        // Adopt the converted HTML ONLY if the editor still holds exactly what was seeded. The
        // conversion is fast, but "fast" is not "atomic" — a user who started typing during the
        // round trip must not have their sentence replaced by the model's original text. If they
        // did type, the markdown they see stays as they left it and their save persists that;
        // losing the formatting is recoverable, losing their words is not.
        if (editor.getText() === generatedContent) {
          editor.commands.setContent(result.content)
        }
        onError(null)
      })
      .catch((error) => {
        if (cancelled) return
        // The text is still on screen and still theirs — but nothing can persist it until this
        // succeeds, so the banner says so rather than letting them type into a dead page.
        onError(describeFailure(error, CONVERT_FAILED_MESSAGE))
      })
    return () => {
      cancelled = true
    }
  }, [generationId, generatedContent, editor, setDocumentId, setVersion, onError])
}
