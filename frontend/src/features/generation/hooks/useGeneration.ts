import { useCallback, useEffect, useRef, useState } from 'react'
import { createGeneration, getGeneration } from '../api/generationApi'
import { SessionExpiredError } from '../../auth/api/authorizedRequest'

export type GenerationUiState = 'idle' | 'pending' | 'completed' | 'failed'

const POLL_INTERVAL_MS = 5000
const MAX_POLL_ATTEMPTS = 60 // ~5 minutes at POLL_INTERVAL_MS

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
const MAX_CONSECUTIVE_POLL_FAILURES = 3

export interface UseGeneration {
  state: GenerationUiState
  content: string | null
  volumePages: number | null
  createdAt: string | null
  error: string | null
  submit: (topic: string) => void
  reset: () => void
}

export function useGeneration(): UseGeneration {
  const [state, setState] = useState<GenerationUiState>('idle')
  const [content, setContent] = useState<string | null>(null)
  const [volumePages, setVolumePages] = useState<number | null>(null)
  const [createdAt, setCreatedAt] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
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
        setError('Превышено время ожидания генерации')
        setState('failed')
        return
      }
      try {
        const res = await getGeneration(id)
        consecutiveFailuresRef.current = 0
        if (res.status === 'completed') {
          stopPolling()
          setContent(res.content)
          setVolumePages(res.volumePages)
          setCreatedAt(res.createdAt)
          setState('completed')
        } else if (res.status === 'failed') {
          stopPolling()
          setError('Не удалось завершить генерацию')
          setState('failed')
        }
        // pending / in_progress → keep polling
      } catch (e) {
        // An expired session will not fix itself by asking again, and every further attempt is a
        // guaranteed 401. It ends the poll immediately, carrying its own message.
        if (e instanceof SessionExpiredError) {
          stopPolling()
          setError(e.message)
          setState('failed')
          return
        }
        // Anything else may be transient. The generation is still running on the server, so a
        // missed status check is not a failed generation — only giving up on it is.
        consecutiveFailuresRef.current += 1
        if (consecutiveFailuresRef.current >= MAX_CONSECUTIVE_POLL_FAILURES) {
          stopPolling()
          setError(e instanceof Error ? e.message : 'Ошибка сети')
          setState('failed')
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
    async (topic: string) => {
      setState('pending')
      setContent(null)
      setVolumePages(null)
      setCreatedAt(null)
      setError(null)
      stopPolling()
      attemptsRef.current = 0
      consecutiveFailuresRef.current = 0
      try {
        const { generationId } = await createGeneration(topic)
        void poll(generationId) // immediate first check
        intervalRef.current = window.setInterval(() => {
          void poll(generationId)
        }, POLL_INTERVAL_MS)
      } catch (e) {
        stopPolling()
        setError(e instanceof Error ? e.message : 'Не удалось создать запрос')
        setState('failed')
      }
    },
    [poll, stopPolling],
  )

  const reset = useCallback(() => {
    stopPolling()
    setState('idle')
    setContent(null)
    setVolumePages(null)
    setCreatedAt(null)
    setError(null)
  }, [stopPolling])

  // Clean up any running interval on unmount.
  useEffect(() => stopPolling, [stopPolling])

  return { state, content, volumePages, createdAt, error, submit, reset }
}
