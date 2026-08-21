import { useCallback, useEffect, useReducer, useRef } from 'react'
import { createGeneration, getGeneration } from '../api/generationApi'
import type { GenerationParameters } from '../utils/generationParameters'
import { SessionExpiredError } from '../../../shared/session/authorizedRequest'
import type { DocumentType } from '../../../shared/domain/documentTypes'
import { describeFailure } from '../../../shared/api/send'
import { RUNTIME } from '../../../shared/config/runtime'
import {
  generationReducer,
  IDLE_GENERATION,
  type GenerationUiState,
} from '../utils/generationState'

export type { GenerationUiState }

// The FIRST gap between status checks, and the two numbers that grow it. See
// `shared/config/runtime` for why 1.5 and 30s.
const POLL_BASE_INTERVAL_MS = RUNTIME.generationPollIntervalMs
const POLL_BACKOFF_FACTOR = RUNTIME.generationPollBackoffFactor
const POLL_MAX_INTERVAL_MS = RUNTIME.generationPollMaxIntervalMs
const MAX_POLL_ATTEMPTS = RUNTIME.generationPollMaxAttempts

// How many CONSECUTIVE failed status checks are tolerated before the generation is called lost.
// Not zero, which is what this was: a single rejection stopped the poll and declared `failed`,
// so one 502 from the proxy threw away a document the server was still writing. Small all the
// same — a status endpoint that is genuinely down must be reported promptly. See
// `shared/config/runtime` for the number.
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
  // Whatever the platform's timer id is: `number` in the browser, an object in Node's types.
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  // The gap before the NEXT check. Grows while nothing changes, reset by any change of status.
  const delayRef = useRef(POLL_BASE_INTERVAL_MS)
  // Whether the chain should keep going. A `setTimeout` chain has no handle to cancel "the next
  // link" while the current one is awaiting a response, so stopping has to be a fact the callback
  // reads after its await, not only a `clearTimeout`.
  const activeRef = useRef(false)
  // The last status the server reported, to notice a transition.
  const lastStatusRef = useRef<string | null>(null)
  const attemptsRef = useRef(0)
  // Consecutive, not total: reset by any successful check, so a poll that misses once every
  // couple of minutes rides out the whole generation instead of accumulating toward a limit.
  const consecutiveFailuresRef = useRef(0)

  const stopPolling = useCallback(() => {
    activeRef.current = false
    if (timeoutRef.current !== null) {
      clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }
  }, [])

  // A tick may arrive while the previous check is still out: the first gap is 5s and the shared
  // request timeout allows 25s, so a slow backend stacks concurrent status calls for one
  // generation. The duplicate traffic is the lesser problem — each stacked call also spends an
  // attempt, so the MAX_POLL_ATTEMPTS budget drains without any extra time passing and the
  // "~5 minutes" ceiling can expire in one. Skipping a tick costs nothing: another one is
  // scheduled and the status has not changed in the meantime.
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
        // A transition is the one moment the next answer is likely to be interesting again, so the
        // backoff collapses back to the base interval; an unchanged status leaves it growing.
        if (res.status !== lastStatusRef.current) {
          lastStatusRef.current = res.status
          delayRef.current = POLL_BASE_INTERVAL_MS
        }
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

  // A self-rescheduling chain rather than `setInterval`. An interval asks at a fixed cadence
  // forever — sixty identical questions over a five-minute generation, all but the last few
  // answered "still working" — and it keeps firing at full rate against a backend that is already
  // struggling. Each link here waits longer than the last (up to the ceiling), so a run that drags
  // on costs progressively less traffic, while a run that changes state pulls the delay back down.
  //
  // The next link is scheduled only after the current check has SETTLED, which also means a slow
  // response can never be overtaken by its own successor.
  const scheduleNextPoll = useCallback(
    (id: string) => {
      const delay = delayRef.current
      delayRef.current = Math.min(POLL_MAX_INTERVAL_MS, Math.round(delay * POLL_BACKOFF_FACTOR))
      timeoutRef.current = setTimeout(() => {
        timeoutRef.current = null
        void poll(id).finally(() => {
          if (activeRef.current) scheduleNextPoll(id)
        })
      }, delay)
    },
    [poll],
  )

  const submit = useCallback(
    async (topic: string, documentType?: DocumentType, parameters?: GenerationParameters) => {
      dispatch({ type: 'submitted' })
      stopPolling()
      attemptsRef.current = 0
      consecutiveFailuresRef.current = 0
      delayRef.current = POLL_BASE_INTERVAL_MS
      lastStatusRef.current = null
      try {
        const { generationId } = await createGeneration(topic, documentType, parameters)
        dispatch({ type: 'accepted', generationId })
        activeRef.current = true
        void poll(generationId) // immediate first check
        scheduleNextPoll(generationId)
      } catch (e) {
        stopPolling()
        dispatch({ type: 'failed', message: describeFailure(e, 'Не удалось создать запрос') })
      }
    },
    [poll, scheduleNextPoll, stopPolling],
  )

  const reset = useCallback(() => {
    stopPolling()
    dispatch({ type: 'reset' })
  }, [stopPolling])

  // Clean up any pending tick on unmount.
  useEffect(() => stopPolling, [stopPolling])

  return { ...run, submit, reset }
}
