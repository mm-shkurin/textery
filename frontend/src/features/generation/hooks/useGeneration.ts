import { useCallback, useEffect, useRef, useState } from 'react'
import { createGeneration, getGeneration } from '../api/generationApi'

export type GenerationUiState = 'idle' | 'pending' | 'completed' | 'failed'

const POLL_INTERVAL_MS = 5000

export interface UseGeneration {
  state: GenerationUiState
  content: string | null
  error: string | null
  submit: (topic: string) => void
  reset: () => void
}

export function useGeneration(): UseGeneration {
  const [state, setState] = useState<GenerationUiState>('idle')
  const [content, setContent] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<number | null>(null)

  const stopPolling = useCallback(() => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  const poll = useCallback(
    async (id: string) => {
      try {
        const res = await getGeneration(id)
        if (res.status === 'completed') {
          stopPolling()
          setContent(res.content)
          setState('completed')
        } else if (res.status === 'failed') {
          stopPolling()
          setError('Не удалось завершить генерацию')
          setState('failed')
        }
        // pending / in_progress → keep polling
      } catch (e) {
        stopPolling()
        setError(e instanceof Error ? e.message : 'Ошибка сети')
        setState('failed')
      }
    },
    [stopPolling],
  )

  const submit = useCallback(
    async (topic: string) => {
      setState('pending')
      setContent(null)
      setError(null)
      stopPolling()
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
    setError(null)
  }, [stopPolling])

  // Clean up any running interval on unmount.
  useEffect(() => stopPolling, [stopPolling])

  return { state, content, error, submit, reset }
}
