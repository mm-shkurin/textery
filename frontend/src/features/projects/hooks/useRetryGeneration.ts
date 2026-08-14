import { useCallback, useRef, useState } from 'react'
import { describeFailure } from '../../../shared/api/send'
import { retryGeneration, RETRY_FAILURE_FALLBACK } from '../api/retryGenerationApi'

export interface RetryState {
  pendingId: string | null
  error: { id: string; message: string } | null
}

/**
 * The «Повторить» command, with the guards a paid, side-effecting button needs.
 *
 * Not optimistic: no new card is shown until the server confirms one. A card rendered on the
 * click and removed on failure is indistinguishable, for the second it exists, from work that
 * actually started — and on this screen "it started" means a model was billed.
 *
 * The idempotency key is minted once per SOURCE and kept until an attempt for that source is
 * CONFIRMED, so a double-click, a second tab and a re-send after a lost response all collapse onto
 * one generation. It survives a failure on purpose: the failure this guards is the one where the
 * request reached the server and only the response was lost, and a fresh key there would bill a
 * second generation for work already running. It is dropped on success, because the user's next
 * «Повторить» on that row is a new command rather than a replay of the one that landed.
 */
export function useRetryGeneration(onRetried: () => void) {
  const [state, setState] = useState<RetryState>({ pendingId: null, error: null })
  const keys = useRef(new Map<string, string>())
  // In-flight ids live in a ref, not in state: two clicks in the same tick both read the state
  // value from before the first render, so a state-based guard lets the second through.
  const inFlight = useRef(new Set<string>())

  const retry = useCallback(
    async (generationId: string) => {
      if (inFlight.current.has(generationId)) return
      inFlight.current.add(generationId)

      let key = keys.current.get(generationId)
      if (key === undefined) {
        key = crypto.randomUUID()
        keys.current.set(generationId, key)
      }

      setState({ pendingId: generationId, error: null })
      try {
        await retryGeneration(generationId, key)
        // Confirmed. The next click on this row is a NEW attempt and needs its own key — reusing
        // this one would have the server collapse it onto the generation just produced, and the
        // button would look broken.
        keys.current.delete(generationId)
        setState({ pendingId: null, error: null })
        // Refetch rather than splice the new row in locally: the server decides the order, and a
        // card inserted here would sit wherever the client guessed until the next load.
        onRetried()
      } catch (failure: unknown) {
        setState({
          pendingId: null,
          error: { id: generationId, message: describeFailure(failure, RETRY_FAILURE_FALLBACK) },
        })
      } finally {
        inFlight.current.delete(generationId)
      }
    },
    [onRetried],
  )

  return { ...state, retry }
}
