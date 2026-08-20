import { useCallback, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { deleteDocument, type DocumentSummary } from '../api/historyApi'
import { describeFailure } from '../../../shared/api/send'

interface DeleteDocumentState {
  // The row awaiting confirmation, or null when no confirmation is open. The document itself and
  // not just its id: the dialog names the work being deleted, and re-finding the row by id in the
  // loaded pages would break the moment the list is filtered out from under it.
  pending: DocumentSummary | null
  isDeleting: boolean
  error: string | null
  request: (entry: DocumentSummary) => void
  cancel: () => void
  confirm: () => void
}

/**
 * The confirm-then-delete cycle behind «удалить текст из истории».
 *
 * Deleting is irreversible and the control is a small ✕ sitting one row away from twenty others,
 * so the confirmation is not optional — it is the only thing standing between a mis-click and
 * work the user cannot get back.
 *
 * On success the history queries are INVALIDATED rather than edited in place. The list is paged
 * by keyset cursor: splicing a row out of a cached page leaves the following pages anchored to
 * cursors computed before the delete, so «показать ещё» would skip a row for every one removed.
 */
export function useDeleteDocument(): DeleteDocumentState {
  const [pending, setPending] = useState<DocumentSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()
  // The in-flight flag lives in a ref, not in the mutation's `isPending`. Two clicks in the same
  // tick both read the state value from before the first render, so a state-based guard lets the
  // second through — and the second DELETE answers 404, the first having already succeeded, which
  // surfaces as a failure for an operation that actually worked. Same reason `useRetryGeneration`
  // keeps its own ref.
  const inFlight = useRef(false)

  const mutation = useMutation({
    mutationFn: (entry: DocumentSummary) => deleteDocument(entry.documentId),
    onSuccess: async () => {
      inFlight.current = false
      setPending(null)
      setError(null)
      // Every history query, not only the one currently on screen: the same document appears
      // under each filter combination the user has visited this session, and leaving those cached
      // pages alone means clearing the search box brings the deleted row back.
      await queryClient.invalidateQueries({ queryKey: ['history'] })
    },
    onError: (cause: unknown) => {
      inFlight.current = false
      // The dialog stays OPEN on failure. Closing it would leave the row on screen with no
      // explanation, which reads as "the delete silently did nothing".
      setError(describeFailure(cause, 'Не удалось удалить работу'))
    },
  })

  const request = useCallback((entry: DocumentSummary) => {
    setError(null)
    setPending(entry)
  }, [])

  const cancel = useCallback(() => {
    // Deliberately does NOT clear `inFlight`: the request is already gone, and re-opening the
    // dialog on another row must not let a second DELETE ride out under the first one's flag.
    // The mutation's own settle handlers are what release it.
    setPending(null)
    setError(null)
  }, [])

  const { mutate, isPending: isDeleting } = mutation
  const confirm = useCallback(() => {
    // No target is a programming error; a second confirm mid-request is the race the ref closes.
    if (pending === null || inFlight.current) return
    inFlight.current = true
    mutate(pending)
  }, [pending, mutate])

  return { pending, isDeleting, error, request, cancel, confirm }
}
