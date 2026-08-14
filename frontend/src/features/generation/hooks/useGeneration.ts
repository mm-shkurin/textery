import { useCallback, useEffect, useReducer, useRef } from 'react'
import { createGeneration, getGeneration } from '../api/generationApi'
import type { GenerationParameters } from '../generationParameters'
import { SessionExpiredError } from '../../auth/api/authorizedRequest'
import type { DocumentType } from '../../../shared/documentTypes'
import { describeFailure } from '../../../shared/api/send'
import { RUNTIME } from '../../../shared/config/runtime'
import {
  generationReducer,
  IDLE_GENERATION,
  type GenerationUiState,
} from './generationState'

export type { GenerationUiState }

const POLL_INTERVAL_MS = RUNTIME.generationPollIntervalMs
const MAX_POLL_ATTEMPTS = RUNTIME.generationPollMaxAttempts

// How many CONSECUTIVE failed status checks are tolerated before the generation is called lost.
//
// Not zero, which is what this was: a single rejection stopped the poll and declared `failed`. The
// generation runs on the server for minutes, and one 502 from the proxy or one dropped packet
// anywhere in that window would throw away work that was still running and completed fine — the
// user is told it failed while the document is being written. Over ~5 minutes of polling, one
// transient error is likely rather than exceptional, so treating it as fatal made the failure
// mode routine.
//
// Three because it must be small: a status endpoint that is genuinely down should be reported
// promptly, not after a minute of silent retrying. Three misses is ~15s of tolerance.
const MAX_CONSECUTIVE_POLL_FAILURES = RUNTIME.generationPollMaxConsecutiveFailures

export interface UseGeneration {
  state: GenerationUiState
  content: string | null
  // The id of the run currently being watched. Exposed because the completed generation has to be
  // CONVERTED into a document before the editor can save anything, and that conversion
  // (`POST /documents/from-generation`) takes the id — not the text. Null until `submit` gets the
  // POST's response back, which is also the moment polling starts.
  generationId: string | null
  volumePages: number | null
  createdAt: string | null
  error: string | null
  // The document type the user picked travels with the topic: it is the ONE field that carries
  // that choice to the backend, and dropping it here would generate a доклад whatever card was
  // pressed. Optional for the same read-only-tests reason as createGeneration's parameter.
  submit: (topic: string, documentType?: DocumentType, parameters?: GenerationParameters) => void
  reset: () => void
}

export function useGeneration(): UseGeneration {
  const [run, dispatch] = useReducer(generationReducer, IDLE_GENERATION)
  const intervalRef = useRef<number | null>(null)
  const attemptsRef = useRef(0)
  // Consecutive, not total: reset by any successful check, so a poll that misses once every
  // couple of minutes rides out the whole generation instead of accumulating toward a limit.
  const consecutiveFailuresRef = useRef(0)

  const stopPolling = useCallback(() => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  // A tick may arrive while the previous check is still out: the interval is 5s and the shared
  // request timeout allows 25s, so a slow backend stacks up to five concurrent status calls for
  // one generation. The duplicate traffic is the lesser problem — each stacked call also spends
  // an attempt, so the MAX_POLL_ATTEMPTS budget drains without any extra time passing and the
  // "~5 minutes" ceiling can expire in one. Skipping a tick costs nothing: the next one is 5s
  // away and the status has not changed in the meantime.
  const inFlightRef = useRef(false)

  const runPollAttempt = useCallback(
    async (id: string) => {
      attemptsRef.current += 1
      if (attemptsRef.current > MAX_POLL_ATTEMPTS) {
        stopPolling()
        dispatch({ type: 'failed', message: 'Превышено время ожидания генерации' })
        return
      }
      try {
        const res = await getGeneration(id)
        consecutiveFailuresRef.current = 0
        if (res.status === 'completed') {
          stopPolling()
          dispatch({
            type: 'completed',
            content: res.content,
            volumePages: res.volumePages,
            createdAt: res.createdAt,
          })
        } else if (res.status === 'failed') {
          stopPolling()
          dispatch({ type: 'failed', message: 'Не удалось завершить генерацию' })
        }
        // pending / in_progress → keep polling
      } catch (e) {
        // An expired session will not fix itself by asking again, and every further attempt is a
        // guaranteed 401. It ends the poll immediately, carrying its own message.
        if (e instanceof SessionExpiredError) {
          stopPolling()
          dispatch({ type: 'failed', message: e.message })
          return
        }
        // Anything else may be transient. The generation is still running on the server, so a
        // missed status check is not a failed generation — only giving up on it is.
        consecutiveFailuresRef.current += 1
        if (consecutiveFailuresRef.current >= MAX_CONSECUTIVE_POLL_FAILURES) {
          stopPolling()
          // `describeFailure`, not `e.message`: a 5xx now arrives as a bare `HttpError` object,
          // and the status is the only fact the user can quote when reporting a poll that gave up.
          dispatch({ type: 'failed', message: describeFailure(e, 'Ошибка сети') })
        }
      }
    },
    [stopPolling],
  )

  const poll = useCallback(
    async (id: string) => {
      if (inFlightRef.current) return
      inFlightRef.current = true
      try {
        await runPollAttempt(id)
      } finally {
        inFlightRef.current = false
      }
    },
    [runPollAttempt],
  )

  const submit = useCallback(
    async (topic: string, documentType?: DocumentType, parameters?: GenerationParameters) => {
      dispatch({ type: 'submitted' })
      stopPolling()
      attemptsRef.current = 0
      consecutiveFailuresRef.current = 0
      try {
        const { generationId } = await createGeneration(topic, documentType, parameters)
        dispatch({ type: 'accepted', generationId })
        void poll(generationId) // immediate first check
        intervalRef.current = setInterval(() => {
          void poll(generationId)
        }, POLL_INTERVAL_MS)
      } catch (e) {
        stopPolling()
        dispatch({ type: 'failed', message: describeFailure(e, 'Не удалось создать запрос') })
      }
    },
    [poll, stopPolling],
  )

  const reset = useCallback(() => {
    stopPolling()
    dispatch({ type: 'reset' })
  }, [stopPolling])

  // Clean up any running interval on unmount.
  useEffect(() => stopPolling, [stopPolling])

  return { ...run, submit, reset }
}
