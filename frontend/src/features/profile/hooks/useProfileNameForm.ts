import { useRef, useState } from 'react'
import {
  NameRejectedError,
  saveProfileName,
  type Profile,
} from '../../../shared/identity/api/profileApi'
import { applyProfile } from '../../../shared/identity/identityStore'
import { nameRejectionMessage, overLengthMessage, RAW_INPUT_TOO_LARGE_MESSAGE } from '../utils/profileCopy'
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

// The display-name form's whole behaviour, kept out of the markup so the two length units and the
// one-PATCH guarantee are readable in one place.
export function useProfileNameForm(profile: Profile, tracking: DirtyTracking) {
  const [value, setValue] = useState(profile.name ?? '')
  const [saving, setSaving] = useState(false)
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [saveFailed, setSaveFailed] = useState(false)
  // How many saves have LANDED. The confirmation toast keys off it: a counter re-fires for a
  // second save where a boolean, already true, would show nothing.
  const [savedCount, setSavedCount] = useState(0)
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
    setFieldError(null)
    setSaveFailed(false)
    if (isNameChanged(next, profile.name)) tracking.markDirty()
    else tracking.markClean()
  }

  function cancel(): void {
    setValue(profile.name ?? '')
    setFieldError(null)
    setSaveFailed(false)
    tracking.markClean()
  }

  async function save(): Promise<void> {
    if (!canSave || savingRef.current) return
    savingRef.current = true
    setSaving(true)
    setFieldError(null)
    setSaveFailed(false)
    try {
      const updated = await saveProfileName(normalized)
      // No second GET: the PATCH response IS the profile, and it carries the normalized value.
      applyProfile(updated)
      setValue(updated.name ?? '')
      setSavedCount((count) => count + 1)
      tracking.markClean()
    } catch (error) {
      if (error instanceof NameRejectedError) {
        setFieldError(nameRejectionMessage(error.errorCode))
      } else {
        // Nothing was stored, the typed value is still the user's, and the form stays usable —
        // the banner offers «Повторить» rather than swallowing the attempt.
        setSaveFailed(true)
      }
    } finally {
      savingRef.current = false
      setSaving(false)
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
