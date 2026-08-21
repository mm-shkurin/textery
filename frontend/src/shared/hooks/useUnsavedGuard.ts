import { useCallback, useEffect, useRef } from 'react'
import { browserWindow, listen } from '../lib/browser'

// Scenario 5.8 — protect un-submitted registration input from being silently discarded.
// Two navigation surfaces need guarding, and they fire on different events:
//   - full-page unload / refresh / tab close → the `beforeunload` event, and
//   - in-app react-router navigation (clicking the footer login <Link>) → NO `beforeunload`
//     at all, so it needs its own explicit confirm at the click seam.
// `isDirty` lives in a component-scoped ref (never a module global): the ref keeps the
// beforeunload effect reading the live value without re-subscribing, and the effect returns a
// cleanup so the listener + dirty state never leak past unmount onto login/verify/workspace.
// The message names the SCREEN, so it cannot be a module constant baked into the hook: this hook
// is reused by the profile screen, and the first version hard-coded «страницу регистрации» —
// a user editing their display name would have been asked about a registration form they are not
// on. Each caller supplies its own; the parameter is required rather than defaulted, so adopting
// the hook on a third screen cannot silently inherit somebody else's wording.
export const UNSAVED_LEAVE_MESSAGE_REGISTER =
  'Введённые данные не сохранены. Покинуть страницу регистрации?'
export const UNSAVED_LEAVE_MESSAGE_PROFILE = 'Имя не сохранено. Покинуть страницу профиля?'

export function useUnsavedGuard(leaveMessage: string) {
  const isDirtyRef = useRef(false)

  useEffect(() => {
    function handleBeforeUnload(event: BeforeUnloadEvent) {
      if (isDirtyRef.current) {
        // preventDefault (not returnValue alone) is what marks the event cancelled, which is
        // the browser's signal to show the native "leave?" prompt.
        event.preventDefault()
      }
    }
    return listen('beforeunload', handleBeforeUnload)
  }, [])

  const markDirty = useCallback(() => {
    isDirtyRef.current = true
  }, [])

  const markClean = useCallback(() => {
    isDirtyRef.current = false
  }, [])

  // Returns true when it is safe to leave: either the form is pristine, or the user confirmed
  // the prompt. Callers prevent the navigation when this returns false.
  const confirmLeave = useCallback(() => {
    if (!isDirtyRef.current) return true
    return browserWindow()?.confirm(leaveMessage) ?? true
  }, [leaveMessage])

  return { markDirty, markClean, confirmLeave }
}
