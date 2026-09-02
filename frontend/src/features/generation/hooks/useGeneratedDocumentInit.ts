import { useEffect, useRef } from 'react'
import type { Editor } from '@tiptap/react'
import { createDocumentFromGeneration } from '../api/documentApi'
import { describeFailure } from '../../../shared/api/send'
import { trackEditorOpened } from '../../../shared/analytics/trackers'

export const CONVERT_FAILED_MESSAGE =
  'Не удалось открыть сгенерированный документ. Проверьте соединение и обновите страницу — до этого сохранение недоступно.'

// The auto path's init (story 18, scenarios 2.1–2.3), split from useDocumentInit because it is a
// different operation with a different failure mode: the manual paths GET or POST a document, this
// one CONVERTS a generation into one. It produces the documentId and version without which the
// editor can neither save nor export, and the converted HTML that turns `## Введение` from a
// literal line of text into a heading.
//
// The response is the only source of the editor's content — not the generation's own markdown, and
// not a follow-up GET.
//
// Not the markdown, because seeding it first and adopting the conversion after was tried and is a
// data-loss bug, observed against the live stack 2026-07-31: the seed marks the document dirty, the
// autosave debounce fires ~1s later, and the RAW markdown is written straight over the converted
// HTML the server just stored. The editor then holds `## Введение` as plain text, permanently, and
// the document in the database has been overwritten to match. Any "seed, then adopt if untouched"
// scheme has to win a race against its own autosave to be correct; not seeding has no race.
//
// Not a follow-up GET, because on a multi-instance backend the read can land on an instance that
// has not yet seen the insert, and the editor would open empty on text that is already stored.
export function useGeneratedDocumentInit({
  generationId,
  editor,
  setDocumentId,
  setVersion,
  onReady,
  onError,
}: {
  generationId?: string
  editor: Editor | null
  setDocumentId: (id: string) => void
  setVersion: (version: number) => void
  // Called once the editor holds exactly what the server holds. ManualEditor mounts dirty (it has
  // no document yet and nothing to compare against), so without this the freshly converted
  // document sits under a «не сохранено» badge with beforeunload armed — and the next autosave
  // tick writes it back to the server unchanged.
  onReady: () => void
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
  // Convert once, ever — the guard is on the REQUEST, not on the effect, because the effect
  // legitimately re-runs when the editor instance arrives.
  const convertedRef = useRef(false)

  // The callbacks are read through refs so they can stay OUT of the dependency array below, and
  // that is a correctness fix rather than a tidy-up. `ManualEditor` passes
  // `onReady: () => setHasUnsavedChanges(false)` — a new identity on every render — so with the
  // callbacks as dependencies the effect re-ran on every render. Each re-run's cleanup set
  // `cancelled = true` on the run holding the in-flight POST, while the new run returned at once
  // because `convertedRef` was already true: when the response finally arrived there was nobody
  // left to apply it, and `setContent` never ran. The conversion still SUCCEEDED, so the document
  // was on the server and in «Мои проекты» while the editor on screen stayed empty and no error
  // was shown. Reported from production 2026-09-02.
  const onReadyRef = useRef(onReady)
  const onErrorRef = useRef(onError)
  const setDocumentIdRef = useRef(setDocumentId)
  const setVersionRef = useRef(setVersion)
  onReadyRef.current = onReady
  onErrorRef.current = onError
  setDocumentIdRef.current = setDocumentId
  setVersionRef.current = setVersion

  useEffect(() => {
    if (generationId === undefined || !editor || convertedRef.current) return
    convertedRef.current = true

    let cancelled = false
    createDocumentFromGeneration(generationId, idempotencyKeyRef.current)
      .then((result) => {
        if (cancelled) return
        setDocumentIdRef.current(result.documentId)
        // One opening per DOCUMENT, not per render and not per effect run. The tracker is keyed
        // on the id, so opening the same document twice in one gesture -- which this very hook's
        // comment records StrictMode doing -- is one opening, while opening a second document
        // later in the session is a second one.
        trackEditorOpened(result.documentId)
        // The server's version, not a guess: `useState(1)` would ship a stale token on the first
        // save and collect a 409 blaming a concurrent save that never happened.
        setVersionRef.current(result.version)
        // Only write into the editor if the user has not started typing into it. They can — the
        // editor is live while this request is out — and replacing their sentence with the model's
        // text would be the same "it deleted my report" failure from the other direction. An
        // emptiness check, unlike a string comparison against the markdown, is something the
        // editor can actually answer.
        if (editor.isEmpty) {
          editor.commands.setContent(result.content)
          // The editor now holds exactly what the server holds, so the document is clean. Said
          // explicitly because ManualEditor mounts dirty; leaving it dirty would arm beforeunload
          // and let the next autosave re-send content the server already has.
          onReadyRef.current()
        }
        onErrorRef.current(null)
      })
      .catch((error) => {
        if (cancelled) return
        // Nothing can persist this document until the conversion succeeds, so the banner says so
        // rather than letting the user type into a page that cannot save.
        onErrorRef.current(describeFailure(error, CONVERT_FAILED_MESSAGE))
      })
    return () => {
      cancelled = true
    }
    // The callbacks are deliberately absent, read through refs above instead: as dependencies they
    // re-ran this effect on every render and cancelled the conversion's own response. Only the two
    // values that identify WHICH conversion this is belong here. Same narrowing, for the same
    // reason, as `useDocumentInit`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generationId, editor])
}
