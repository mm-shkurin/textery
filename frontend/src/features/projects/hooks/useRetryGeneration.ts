import { useCallback, useRef, useState } from 'react'
import { describeFailure } from '../../../shared/api/send'
import {
  retryGeneration,
  RETRY_FAILURE_FALLBACK,
  type RetryOverrides,
} from '../api/retryGenerationApi'
import { useIdempotencyKeys } from './useIdempotencyKeys'

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
 * A double-click, a second tab and a re-send after a lost response all collapse onto one
 * generation — see useIdempotencyKeys for the key's lifetime and why it outlives a failure.
 */
export function useRetryGeneration(onRetried: (generationId: string) => void) {
  const [state, setState] = useState<RetryState>({ pendingId: null, error: null })
  const keys = useIdempotencyKeys()
  // In-flight ids live in a ref, not in state: two clicks in the same tick both read the state
  // value from before the first render, so a state-based guard lets the second through.
  const inFlight = useRef(new Set<string>())

  const attempt = useCallback(
    async (generationId: string, overrides?: RetryOverrides) => {
      // The overrides travel with the key, not instead of it: a replay of the SAME click must
      // still collapse onto the generation it already started, whatever it asked for.
      await retryGeneration(generationId, keys.keyFor(generationId), overrides)
      keys.confirm(generationId)
      setState({ pendingId: null, error: null })
      // The row is patched in the cache by the caller and the list is refreshed in the
      // background: the server still decides the order, but the user sees their click land
      // immediately instead of watching the whole grid reload.
      onRetried(generationId)
    },
    [keys, onRetried],
  )

  const retry = useCallback(
    async (generationId: string, overrides?: RetryOverrides) => {
      if (inFlight.current.has(generationId)) return
      inFlight.current.add(generationId)
      setState({ pendingId: generationId, error: null })
      try {
        await attempt(generationId, overrides)
      } catch (failure: unknown) {
        setState({
          pendingId: null,
          error: { id: generationId, message: describeFailure(failure, RETRY_FAILURE_FALLBACK) },
        })
      } finally {
        inFlight.current.delete(generationId)
      }
    },
    [attempt],
  )

  return { ...state, retry }
}
