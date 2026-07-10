import { useCallback, useEffect, useRef, useState } from 'react'
import { createGeneration, getGeneration } from '../api/generationApi'

export type GenerationUiState = 'idle' | 'pending' | 'completed' | 'failed'

const POLL_INTERVAL_MS = 5000
const MAX_POLL_ATTEMPTS = 60 // ~5 minutes at POLL_INTERVAL_MS

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

  const stopPolling = useCallback(() => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  const poll = useCallback(
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
      setVolumePages(null)
      setCreatedAt(null)
      setError(null)
      stopPolling()
      attemptsRef.current = 0
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
