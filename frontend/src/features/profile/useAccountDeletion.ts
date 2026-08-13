import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { clearSession } from '../auth/utils/authSession'
import {
  deletionConfirmationKind,
  requestAccountDeletion,
} from '../../shared/identity/api/deleteAccountApi'
import { DeletionRejectedError } from '../../shared/identity/api/profileErrors'
import { resetIdentity } from '../../shared/identity/identityStore'
import type { Profile } from '../../shared/identity/api/profileApi'
import { DELETION_FAILED_MESSAGE } from './profileCopy'

// Deleting the account: the confirmation gate, the request, and the exit.
//
// THE EXIT IS THE HARD PART. The 204 does not invalidate the access token — these are stateless
// JWTs, so the one in this tab stays syntactically valid for up to fifteen more minutes while the
// backend answers 401 to it, because the account behind it is gone. A `/me` still in flight, or
// one fired by a component that re-renders on the way out, would therefore resolve into an
// expired-session screen: the last thing a user sees on their way out of the product would be an
// error about a session they deliberately ended.
//
// So the order is fixed and is the whole design:
//   1. `resetIdentity()`  — disown in-flight identity/avatar requests, drop the snapshot, revoke
//                           the avatar's object URL.
//   2. `clearSession()`   — drop the tokens, so nothing can start a new authenticated request.
//   3. `navigate('/')`    — replace, so Back cannot return to a screen for an account that no
//                           longer exists.
export function useAccountDeletion(profile: Profile) {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [value, setValue] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Synchronous, unlike `busy`: two clicks in one tick both read the state React has not
  // re-rendered yet. On every other screen that costs a duplicate request; here it would be a
  // second deletion attempt against an account that is already gone, which answers 401 and would
  // be reported as a failure of an operation that succeeded.
  const busyRef = useRef(false)

  const kind = deletionConfirmationKind(profile)
  // The address must match EXACTLY — same case, same characters. Only the surrounding whitespace
  // is forgiven, because a pasted address routinely carries a trailing space and refusing that
  // leaves the user staring at a disabled button with nothing on screen explaining why.
  const confirmed = kind === 'password' ? value !== '' : value.trim() === profile.email

  function openConfirmation(): void {
    setOpen(true)
    setValue('')
    setError(null)
  }

  // Nothing is sent, nothing is kept. Cancelling has to be as cheap as it looks, or the next
  // person hesitates before opening the panel at all.
  function cancel(): void {
    setOpen(false)
    setValue('')
    setError(null)
  }

  async function confirm(): Promise<void> {
    if (!confirmed || busyRef.current) return
    busyRef.current = true
    setBusy(true)
    setError(null)
    try {
      await requestAccountDeletion(
        kind === 'password' ? { kind, password: value } : { kind, email: value.trim() },
      )
      resetIdentity()
      clearSession()
      navigate('/', { replace: true })
    } catch (rejection) {
      // A refused confirmation is NOT a session ending. The user stays exactly where they are,
      // with what they typed still in the field, and the tokens untouched — this is the one
      // failure on this screen where treating it as "you are signed out" would be actively
      // wrong.
      setError(
        rejection instanceof DeletionRejectedError ? rejection.message : DELETION_FAILED_MESSAGE,
      )
    } finally {
      busyRef.current = false
      setBusy(false)
    }
  }

  return { kind, open, value, busy, error, confirmed, openConfirmation, cancel, confirm, setValue }
}
