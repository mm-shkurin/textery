import { useRef, useState } from 'react'
import {
  NameRejectedError,
  saveProfileName,
  type Profile,
} from '../../../shared/identity/api/profileApi'
import { applyProfile } from '../../../shared/identity/identityStore'
import {
  nameRejectionMessage,
  overLengthMessage,
  RAW_INPUT_TOO_LARGE_MESSAGE,
} from '../utils/profileCopy'
import {
  countCodePoints,
  isNameChanged,
  NAME_MAX_CODE_POINTS,
  normalizeName,
  RAW_NAME_MAX_CODE_POINTS,
} from '../../../shared/identity/nameValue'

interface DirtyTracking {
  markDirty: () => void
  markClean: () => void
}

interface SaveAttempt {
  saving: boolean
  fieldError: string | null
  saveFailed: boolean
  // How many saves have LANDED. The confirmation toast keys off it: a counter re-fires for a
  // second save where a boolean, already true, would show nothing.
  savedCount: number
}

const IDLE_ATTEMPT: SaveAttempt = {
  saving: false,
  fieldError: null,
  saveFailed: false,
  savedCount: 0,
}

// The display-name form's whole behaviour, kept out of the markup so the two length units and the
// one-PATCH guarantee are readable in one place.
export function useProfileNameForm(profile: Profile, tracking: DirtyTracking) {
  const [value, setValue] = useState(profile.name ?? '')
  // One state for the whole save attempt rather than four. These four values only ever change
  // together — every edit clears the errors, every save sets and then clears `saving` — and as
  // separate `useState`s each transition was three or four calls that a future edit could get
  // half-right, leaving a stale error visible next to a fresh success.
  const [attempt, setAttempt] = useState<SaveAttempt>(IDLE_ATTEMPT)
  const { saving, fieldError, saveFailed, savedCount } = attempt
  // A ref, not the `saving` state: two clicks in the same tick both read the state React has not
  // re-rendered yet, and the user gets two PATCHes for one save. Double-click and double-Enter
  // are the same event twice, and the guard has to be synchronous to see the second one.
  const savingRef = useRef(false)

  const normalized = normalizeName(value)
  // Counted on the NORMALIZED value and in CODE POINTS — the exact units the server bounds. See
  // nameValue.ts for the two ways this goes silently wrong.
  const count = countCodePoints(normalized)
  const overLength = count > NAME_MAX_CODE_POINTS
  const rawTooLarge = countCodePoints(value) > RAW_NAME_MAX_CODE_POINTS
  // Recomputed against the SAVED profile, which after a save is the server's normalized answer.
  const changed = isNameChanged(value, profile.name)
  const canSave = changed && !overLength && !rawTooLarge && !saving

  const localError = overLength
    ? overLengthMessage(count)
    : rawTooLarge
      ? RAW_INPUT_TOO_LARGE_MESSAGE
      : null

  function change(next: string): void {
    setValue(next)
    clearErrors()
    if (isNameChanged(next, profile.name)) tracking.markDirty()
    else tracking.markClean()
  }

  function cancel(): void {
    setValue(profile.name ?? '')
    clearErrors()
    tracking.markClean()
  }

  function clearErrors(): void {
    setAttempt((previous) => ({ ...previous, fieldError: null, saveFailed: false }))
  }

  async function save(): Promise<void> {
    if (!canSave || savingRef.current) return
    savingRef.current = true
    setAttempt((previous) => ({ ...previous, saving: true, fieldError: null, saveFailed: false }))
    try {
      const updated = await saveProfileName(normalized)
      // No second GET: the PATCH response IS the profile, and it carries the normalized value.
      applyProfile(updated)
      setValue(updated.name ?? '')
      setAttempt((previous) => ({ ...previous, savedCount: previous.savedCount + 1 }))
      tracking.markClean()
    } catch (error) {
      if (error instanceof NameRejectedError) {
        const message = nameRejectionMessage(error.errorCode)
        setAttempt((previous) => ({ ...previous, fieldError: message }))
      } else {
        // Nothing was stored, the typed value is still the user's, and the form stays usable —
        // the banner offers «Повторить» rather than swallowing the attempt.
        setAttempt((previous) => ({ ...previous, saveFailed: true }))
      }
    } finally {
      savingRef.current = false
      setAttempt((previous) => ({ ...previous, saving: false }))
    }
  }

  return {
    value,
    count,
    overLength,
    canSave,
    changed,
    saving,
    savedCount,
    error: fieldError ?? localError,
    saveFailed,
    change,
    cancel,
    save,
  }
}
