import { useCallback, useState } from 'react'

// What the toolbar reports about the current save, as ONE value.
//
// The three facts are one story told at three moments — a write is in flight, a rejected write has
// another attempt scheduled, a write gave up — and every transition the save cycle makes writes at
// least two of them. Held apart they were three independent switches, and a combination such as
// «повторяем…» rendered next to «не сохранено» was one missed setter away.
export interface SaveStatus {
  isSaving: boolean
  // An attempt has been rejected and the capped backoff has another one scheduled. Strictly
  // narrower than isSaving, which is true from before the first request is sent.
  isRetryPending: boolean
  saveError: string | null
}

const IDLE: SaveStatus = { isSaving: false, isRetryPending: false, saveError: null }

// The setters keep their single-boolean shape because the save cycle and the write chain are
// React-free by construction (see autosaveSaveCycle): they are handed plain callbacks, and giving
// them a dispatch would put this hook's action vocabulary into two files that must not know it.
export function useSaveStatus() {
  const [status, setStatus] = useState<SaveStatus>(IDLE)

  const setIsSaving = useCallback(
    (isSaving: boolean) => setStatus((current) => ({ ...current, isSaving })),
    [],
  )
  const setRetryPending = useCallback(
    (isRetryPending: boolean) => setStatus((current) => ({ ...current, isRetryPending })),
    [],
  )
  const setSaveError = useCallback(
    (saveError: string | null) => setStatus((current) => ({ ...current, saveError })),
    [],
  )

  return { status, setIsSaving, setRetryPending, setSaveError }
}
